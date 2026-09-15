"""Experimental 1D-CNN comparison over engineered temporal feature sequences.

This is an optional extension and is not the canonical reported RF benchmark.
"""
from __future__ import annotations

import copy
import random
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
except ImportError as exc:
    raise ImportError(
        "PyTorch is required for the 1D-CNN extension. Install extensions/cnn/requirements.txt."
    ) from exc

from eeg_seizure_detection.config import ExperimentConfig
from eeg_seizure_detection.data import build_patient_matrix_index, collect_rows_from_matrix_index
from eeg_seizure_detection.evaluation import (
    apply_duration_constraint,
    choose_threshold_from_validation,
    compute_event_metrics,
    split_inner_validation_files,
)
from eeg_seizure_detection.models import sample_training_rows


DL_BENCHMARK_CONFIG = {'batch_size': 512, 'epochs': 10, 'patience': 3, 'learning_rate': 0.001, 'weight_decay': 0.0001, 'dropout': 0.25, 'hidden_channels': (96, 64)}

DL_DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

def set_torch_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def reshape_stacked_features_for_cnn(X: np.ndarray, cfg: ExperimentConfig) -> np.ndarray:
    """[, , ]。"""
    X = np.asarray(X, dtype=np.float32)
    seq_len = int(cfg.feature.history_epochs + 1)
    if X.ndim != 2:
        raise ValueError(f'Expected 2D array, got shape={X.shape}')
    if X.shape[1] % seq_len != 0:
        raise ValueError(f'Input dim {X.shape[1]} cannot be evenly split into seq_len={seq_len}.')
    base_dim = X.shape[1] // seq_len
    return X.reshape(X.shape[0], seq_len, base_dim)

class EEG1DCNN(nn.Module):
    """1D CNN， epoch 。"""

    def __init__(self, base_dim: int, dropout: float=0.25, hidden_channels: Tuple[int, int]=(96, 64)):
        super().__init__()
        c1, c2 = hidden_channels
        self.encoder = nn.Sequential(nn.Conv1d(base_dim, c1, kernel_size=3, padding=1), nn.BatchNorm1d(c1), nn.ReLU(), nn.Dropout(dropout), nn.Conv1d(c1, c2, kernel_size=3, padding=1), nn.BatchNorm1d(c2), nn.ReLU(), nn.AdaptiveAvgPool1d(1))
        self.head = nn.Sequential(nn.Flatten(), nn.Linear(c2, 32), nn.ReLU(), nn.Dropout(dropout), nn.Linear(32, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.transpose(1, 2)
        x = self.encoder(x)
        x = self.head(x)
        return x.squeeze(1)

def standardize_train_blocks(X_train: np.ndarray, other_blocks: Sequence[np.ndarray]) -> Tuple[np.ndarray, List[np.ndarray], np.ndarray, np.ndarray]:
    """，。"""
    mean = X_train.mean(axis=0, keepdims=True).astype(np.float32)
    std = X_train.std(axis=0, keepdims=True).astype(np.float32)
    std[std < 1e-06] = 1.0
    X_train_norm = ((X_train - mean) / std).astype(np.float32)
    normalized_blocks = [((np.asarray(block, dtype=np.float32) - mean) / std).astype(np.float32) for block in other_blocks]
    return (X_train_norm, normalized_blocks, mean, std)

def _build_loader(X: np.ndarray, y: np.ndarray, batch_size: int, shuffle: bool) -> DataLoader:
    dataset = TensorDataset(torch.from_numpy(np.asarray(X, dtype=np.float32)), torch.from_numpy(np.asarray(y, dtype=np.float32)))
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)

def train_1dcnn_classifier(X_train: np.ndarray, y_train: np.ndarray, cfg: ExperimentConfig, seed: int, X_val: Optional[np.ndarray]=None, y_val: Optional[np.ndarray]=None, dl_cfg: Optional[Dict[str, Any]]=None) -> Dict[str, Any]:
    """1D CNN，。"""
    dl_cfg = DL_BENCHMARK_CONFIG if dl_cfg is None else dl_cfg
    set_torch_seed(int(seed))
    X_train = np.asarray(X_train, dtype=np.float32)
    y_train = np.asarray(y_train, dtype=np.int8)
    extra_blocks = []
    if X_val is not None:
        extra_blocks.append(np.asarray(X_val, dtype=np.float32))
    X_train_norm, transformed_blocks, mean, std = standardize_train_blocks(X_train, extra_blocks)
    X_train_seq = reshape_stacked_features_for_cnn(X_train_norm, cfg)
    X_val_seq = None
    if X_val is not None:
        X_val_seq = reshape_stacked_features_for_cnn(transformed_blocks[0], cfg)
        y_val = np.asarray(y_val, dtype=np.int8)
    model = EEG1DCNN(base_dim=int(X_train_seq.shape[2]), dropout=float(dl_cfg['dropout']), hidden_channels=tuple(dl_cfg['hidden_channels'])).to(DL_DEVICE)
    pos = max(1, int(np.sum(y_train == 1)))
    neg = max(1, int(np.sum(y_train == 0)))
    pos_weight = torch.tensor([neg / pos], dtype=torch.float32, device=DL_DEVICE)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(dl_cfg['learning_rate']), weight_decay=float(dl_cfg['weight_decay']))
    train_loader = _build_loader(X_train_seq, y_train, batch_size=int(dl_cfg['batch_size']), shuffle=True)
    best_state = copy.deepcopy(model.state_dict())
    best_metric = float('inf')
    epochs_no_improve = 0
    history_rows = []
    for epoch in range(int(dl_cfg['epochs'])):
        model.train()
        train_loss_sum = 0.0
        train_count = 0
        for xb, yb in train_loader:
            xb = xb.to(DL_DEVICE)
            yb = yb.to(DL_DEVICE)
            optimizer.zero_grad(set_to_none=True)
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()
            batch_n = int(len(yb))
            train_loss_sum += float(loss.item()) * batch_n
            train_count += batch_n
        train_loss = train_loss_sum / max(1, train_count)
        if X_val_seq is None or y_val is None or len(y_val) == 0:
            current_metric = train_loss
            val_loss = np.nan
        else:
            model.eval()
            with torch.no_grad():
                xb = torch.from_numpy(X_val_seq).to(DL_DEVICE)
                yb = torch.from_numpy(y_val.astype(np.float32)).to(DL_DEVICE)
                logits = model(xb)
                val_loss = float(criterion(logits, yb).item())
            current_metric = val_loss
        history_rows.append({'epoch': int(epoch + 1), 'train_loss': float(train_loss), 'val_loss': float(val_loss) if not np.isnan(val_loss) else np.nan})
        if current_metric + 1e-06 < best_metric:
            best_metric = current_metric
            best_state = copy.deepcopy(model.state_dict())
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= int(dl_cfg['patience']):
                break
    model.load_state_dict(best_state)
    model.eval()
    return {'model': model, 'mean': mean, 'std': std, 'history_df': pd.DataFrame(history_rows)}

@torch.no_grad()
def predict_1dcnn_proba(model: nn.Module, X: np.ndarray, cfg: ExperimentConfig, mean: np.ndarray, std: np.ndarray, batch_size: int=2048) -> np.ndarray:
    """。"""
    X = np.asarray(X, dtype=np.float32)
    X_norm = ((X - mean) / std).astype(np.float32)
    X_seq = reshape_stacked_features_for_cnn(X_norm, cfg)
    prob_blocks = []
    for start in range(0, len(X_seq), batch_size):
        xb = torch.from_numpy(X_seq[start:start + batch_size]).to(DL_DEVICE)
        logits = model(xb)
        probs = torch.sigmoid(logits).detach().cpu().numpy()
        prob_blocks.append(probs.astype(np.float32))
    return np.concatenate(prob_blocks, axis=0) if prob_blocks else np.empty((0,), dtype=np.float32)

def evaluate_patient_loso_1dcnn(patient_payload: Dict[str, Any], cfg: ExperimentConfig, patient_seed_offset: int=0, dl_cfg: Optional[Dict[str, Any]]=None) -> Dict[str, Any]:
    """LOSO ， 1D CNN。"""
    patient_id = patient_payload['meta']['patient_id']
    file_payload = patient_payload['files']
    seizure_files = sorted([f for f, d in file_payload.items() if d['has_seizure']])
    bg_files = sorted([f for f, d in file_payload.items() if not d['has_seizure']])
    if len(seizure_files) < 2:
        raise ValueError('Seizure file count < 2; cannot run LOSO.')
    X_all, y_all, file_row_spans = build_patient_matrix_index(patient_payload)
    rng = np.random.default_rng(cfg.eval.random_state + patient_seed_offset)
    shuffled_bg = bg_files.copy()
    rng.shuffle(shuffled_bg)
    bg_chunks = np.array_split(shuffled_bg, len(seizure_files))
    fold_rows = []
    all_y_true = []
    all_y_pred = []
    all_y_score = []
    for outer_idx, test_seizure_file in enumerate(seizure_files):
        outer_train_seizure_files = seizure_files[:outer_idx] + seizure_files[outer_idx + 1:]
        outer_test_bg_files = list(bg_chunks[outer_idx])
        outer_test_bg_set = set(outer_test_bg_files)
        outer_train_bg_files = [f for f in bg_files if f not in outer_test_bg_set]
        inner_train_seizure_files, inner_train_bg_files, val_seizure_files, val_bg_files = split_inner_validation_files(outer_train_seizure_files, outer_train_bg_files, seed=cfg.eval.random_state + patient_seed_offset + outer_idx)
        inner_train_files = inner_train_seizure_files + inner_train_bg_files
        X_inner_raw, y_inner_raw = collect_rows_from_matrix_index(X_all=X_all, y_all=y_all, file_row_spans=file_row_spans, file_names=inner_train_files, feature_indices=None)
        if len(y_inner_raw) == 0:
            raise ValueError('No inner-train samples available in this fold.')
        inner_rng = np.random.default_rng(cfg.eval.random_state + 4000 + outer_idx)
        X_inner_train, y_inner_train = sample_training_rows(X_inner_raw, y_inner_raw, cfg, inner_rng)
        threshold = float(cfg.eval.default_threshold)
        if len(val_seizure_files) > 0:
            X_val, y_val = collect_rows_from_matrix_index(X_all=X_all, y_all=y_all, file_row_spans=file_row_spans, file_names=val_seizure_files + val_bg_files, feature_indices=None)
            inner_bundle = train_1dcnn_classifier(X_train=X_inner_train, y_train=y_inner_train, cfg=cfg, seed=cfg.eval.random_state + 5000 + outer_idx, X_val=X_val, y_val=y_val, dl_cfg=dl_cfg)
            val_scores = predict_1dcnn_proba(inner_bundle['model'], X_val, cfg, mean=inner_bundle['mean'], std=inner_bundle['std'])
            threshold_info = choose_threshold_from_validation(y_val, val_scores, cfg)
            threshold = float(threshold_info['threshold'])
        X_train_outer, y_train_outer = collect_rows_from_matrix_index(X_all=X_all, y_all=y_all, file_row_spans=file_row_spans, file_names=outer_train_seizure_files + outer_train_bg_files, feature_indices=None)
        outer_rng = np.random.default_rng(cfg.eval.random_state + 6000 + outer_idx)
        X_train_outer, y_train_outer = sample_training_rows(X_train_outer, y_train_outer, cfg, outer_rng)
        outer_bundle = train_1dcnn_classifier(X_train=X_train_outer, y_train=y_train_outer, cfg=cfg, seed=cfg.eval.random_state + 7000 + outer_idx, dl_cfg=dl_cfg)
        X_test, y_test = collect_rows_from_matrix_index(X_all=X_all, y_all=y_all, file_row_spans=file_row_spans, file_names=sorted([test_seizure_file] + outer_test_bg_files), feature_indices=None)
        y_score = predict_1dcnn_proba(outer_bundle['model'], X_test, cfg, mean=outer_bundle['mean'], std=outer_bundle['std'])
        y_score_smoothed = medfilt(y_score, kernel_size=5)
        y_pred = (y_score_smoothed >= threshold).astype(np.int8)
        y_pred = apply_duration_constraint(y_pred, cfg.eval.min_duration_epochs)
        fold_metrics = compute_event_metrics(y_test, y_pred, cfg.feature.epoch_len_s)
        fold_rows.append({'fold': int(outer_idx), 'threshold': float(threshold), 'test_seizure_file': test_seizure_file, 'n_test_bg_files': int(len(outer_test_bg_files)), 'sensitivity': fold_metrics['sensitivity'], 'far_per_hour': fold_metrics['far_per_hour'], 'median_delay_s': fold_metrics['median_delay_s']})
        all_y_true.append(y_test)
        all_y_pred.append(y_pred)
        all_y_score.append(y_score_smoothed)
    y_true_cat = np.concatenate(all_y_true)
    y_pred_cat = np.concatenate(all_y_pred)
    y_score_cat = np.concatenate(all_y_score)
    patient_metrics = compute_event_metrics(y_true_cat, y_pred_cat, cfg.feature.epoch_len_s)
    summary = {'Patient': patient_id, 'Model': 'cnn_1d', 'TopK': -1, 'Hours': patient_metrics['hours'], 'True_Seizures': patient_metrics['events'], 'Sensitivity': patient_metrics['sensitivity'], 'FAR_per_Hour': patient_metrics['far_per_hour'], 'Mean_Delay_s': patient_metrics['mean_delay_s'], 'Median_Delay_s': patient_metrics['median_delay_s'], 'Median_Threshold': float(np.median([row['threshold'] for row in fold_rows]))}
    return {'summary': summary, 'folds': pd.DataFrame(fold_rows), 'y_true': y_true_cat, 'y_pred': y_pred_cat, 'y_score': y_score_cat}

def evaluate_many_patients_1dcnn(caches: Dict[str, Dict[str, Any]], cfg: ExperimentConfig, dl_cfg: Optional[Dict[str, Any]]=None) -> Dict[str, Any]:
    """1D CNN LOSO 。"""
    patient_outputs = {}
    summary_rows = []
    for patient_idx, patient_id in enumerate(cfg.eval.patient_ids):
        if patient_id not in caches:
            continue
        try:
            result = evaluate_patient_loso_1dcnn(patient_payload=caches[patient_id], cfg=cfg, patient_seed_offset=patient_idx * 100, dl_cfg=dl_cfg)
            patient_outputs[patient_id] = result
            summary_rows.append(result['summary'])
            print(f"[{patient_id}] cnn_1d | Sens={result['summary']['Sensitivity']:.2%} | FAR/hr={result['summary']['FAR_per_Hour']:.4f} | MedianThr={result['summary']['Median_Threshold']:.3f}")
        except Exception as exc:
            print(f'[]{patient_id}1D CNN :{exc}')
    return {'patient_outputs': patient_outputs, 'summary_df': pd.DataFrame(summary_rows)}
