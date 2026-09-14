"""Reusable core extracted from the canonical EE6019 final notebook.

This generated copy exists only inside github_release. The original notebook is
never edited. The notebook remains the source of truth for reported experiments.
"""
from __future__ import annotations

from __future__ import annotations
import gc
import io
import json
import math
import os
import copy
import random
import re
import sys
import time
import warnings
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import joblib
import matplotlib.pyplot as plt
import mne
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.signal import butter, medfilt, sosfiltfilt
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from xgboost import XGBClassifier

class FeatureConfig:
    epoch_len_s: int = 2
    bandpass_low_hz: float = 0.5
    bandpass_high_hz: float = 50.0
    bandpass_method: str = "butter_sos"   # "butter_sos" or "fir_zero"
    butter_order: int = 4
    band_edges_hz: Tuple[int, ...] = tuple(range(0, 42, 2))   # 0,2,4,...,40
    synchrony_pairs_names: Tuple[Tuple[str, str], ...] = (
        ("FP1-F3", "FP2-F4"),
        ("F7-T7", "F8-T8"),
        ("C3-P3", "C4-P4"),
    )
    history_epochs: int = 3
    scale_to_uV: bool = True
    channel_missing_policy: str = "strict"

class EvalConfig:
    patient_ids: Tuple[str, ...] = tuple(f"chb{i:02d}" for i in range(1, 11))
    threshold_grid: Tuple[float, ...] = tuple(np.round(np.linspace(0.10, 0.95, 50), 3))
    min_duration_epochs: int = 3
    min_acceptable_sensitivity: float = 0.70
    neg_to_pos_ratio: int = 10
    min_neg_samples: int = 3000
    default_threshold: float = 0.50
    fixed_threshold_mode: bool = True
    fixed_threshold_value: float = 0.50

    svm_c: float = 1.0
    svm_gamma: str = "scale"
    rf_n_estimators: int = 300
    rf_max_depth: Optional[int] = None
    rf_min_samples_leaf: int = 1
    rf_max_features: str = "sqrt"
    rf_n_jobs: int = -1

    # XGBoost params
    xgb_n_estimators: int = 100
    xgb_max_depth: int = 6
    xgb_learning_rate: float = 0.05
    xgb_subsample: float = 0.9
    xgb_colsample_bytree: float = 0.9
    xgb_reg_lambda: float = 1.0
    xgb_min_child_weight: float = 1.0
    xgb_gamma: float = 0.0
    xgb_tree_method: str = "hist"
    xgb_n_jobs: int = -1

    top_k_features: int = 50
    selector_n_estimators: int = 80
    selector_max_depth: int = 4
    random_state: int = GLOBAL_SEED

class ExportConfig:
    export_subdir: str = "exported_models"
    model_filename: str = "rf_lightweight_model.joblib"
    metadata_filename: str = "rf_lightweight_metadata.json"
    service_script_filename: str = "serve_model.py"
    client_script_filename: str = "example_client.py"

class ExperimentConfig:
    data_root: str = r"D:\EEG_Data\chb-mit-scalp-eeg-database-1.0.0"
    cache_subdir: str = "feature_cache_refactored"
    feature: FeatureConfig = field(default_factory=FeatureConfig)
    eval: EvalConfig = field(default_factory=EvalConfig)
    export: ExportConfig = field(default_factory=ExportConfig)

    @property
    def channels(self) -> List[str]:
        """Cached: avoids rebuilding the list on every access (optimization #10+#17)."""
        if not hasattr(self, "_channels_cached"):
            ref_ch_names = [
                "FP1-F7", "F7-T7", "T7-P7", "P7-O1",
                "FP1-F3", "F3-C3", "C3-P3", "P3-O1",
                "FP2-F4", "F4-C4", "C4-P4", "P4-O2",
                "FP2-F8", "F8-T8", "T8-P8", "P8-O2",
                "FZ-CZ", "CZ-PZ", "P7-T7", "T7-FT9",
                "FT9-FT10", "FT10-T8", "T8-P8",
            ]
            self._channels_cached = list(dict.fromkeys(ref_ch_names))
        return self._channels_cached

    @property
    def cache_dir(self) -> Path:
        return Path(self.data_root) / self.cache_subdir

    @property
    def export_dir(self) -> Path:
        return Path(self.data_root) / self.export.export_subdir

def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path

def make_json_safe(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    if isinstance(obj, tuple):
        return [make_json_safe(x) for x in obj]
    if isinstance(obj, list):
        return [make_json_safe(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): make_json_safe(v) for k, v in obj.items()}
    return obj

def config_to_hash(cfg: ExperimentConfig) -> str:
    """Cached: avoids re-serializing config on every call (optimization #8)."""
    obj_id = id(cfg)
    cached = _CONFIG_HASH_CACHE.get(obj_id)
    if cached is not None:
        return cached
    cfg_dict = make_json_safe(asdict(cfg))
    hash_payload = {
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        "config": cfg_dict,
    }
    cfg_str = json.dumps(hash_payload, sort_keys=True, ensure_ascii=False)
    result = joblib.hash(cfg_str)
    _CONFIG_HASH_CACHE[obj_id] = result
    return result

def save_json(data: Dict[str, Any], path: Path) -> None:
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(make_json_safe(data), f, ensure_ascii=False, indent=2)

def load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_patient_cache_path(cfg: ExperimentConfig, patient_id: str) -> Path:
    cfg_hash = config_to_hash(cfg)[:12]
    ensure_dir(cfg.cache_dir)
    return cfg.cache_dir / f"{patient_id}_features_{cfg_hash}.joblib"

def get_export_paths(cfg: ExperimentConfig) -> Dict[str, Path]:
    export_dir = ensure_dir(cfg.export_dir)
    return {
        "model": export_dir / cfg.export.model_filename,
        "metadata": export_dir / cfg.export.metadata_filename,
        "service_script": export_dir / cfg.export.service_script_filename,
        "client_script": export_dir / cfg.export.client_script_filename,
    }

def parse_summary_to_dict(summary_path: Path) -> Dict[str, List[Tuple[int, int]]]:
    """
    解析 CHB-MIT 的 patient summary，兼容以下常见变体：
    1) File Name: chb01_03.edf
    2) File Name: chb02_16+.edf
    3) Seizure Start Time: 2996 seconds
    4) Seizure 1 Start Time: 2996 seconds
    """
    seizure_dict: Dict[str, List[Tuple[int, int]]] = {}
    current_file: Optional[str] = None
    current_start: Optional[int] = None

    if not summary_path.exists():
        return seizure_dict

    file_pattern = re.compile(r"File Name:\s*([^\s]+\.edf)", flags=re.IGNORECASE)
    start_pattern = re.compile(
        r"Seizure(?:\s+\d+)?\s+Start Time:\s*(\d+)\s*(?:seconds?)?",
        flags=re.IGNORECASE,
    )
    end_pattern = re.compile(
        r"Seizure(?:\s+\d+)?\s+End Time:\s*(\d+)\s*(?:seconds?)?",
        flags=re.IGNORECASE,
    )

    with open(summary_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.strip()

            file_match = file_pattern.search(line)
            if file_match:
                current_file = Path(file_match.group(1)).name
                seizure_dict.setdefault(current_file, [])
                current_start = None
                continue

            start_match = start_pattern.search(line)
            if start_match:
                current_start = int(start_match.group(1))
                continue

            end_match = end_pattern.search(line)
            if end_match and current_file is not None and current_start is not None:
                current_end = int(end_match.group(1))
                if current_end > current_start:
                    seizure_dict[current_file].append((current_start, current_end))
                current_start = None

    return seizure_dict

def normalize_channel_name(name: str) -> str:
    name = name.strip().upper()
    name = re.sub(r"-\d+$", "", name)
    name = re.sub(r"\s+", "", name)
    return name

def deduplicate_and_normalize_raw(raw: mne.io.BaseRaw) -> mne.io.BaseRaw:
    original_names = raw.ch_names
    normalized_names = [normalize_channel_name(ch) for ch in original_names]

    seen = set()
    to_drop = []
    rename_map = {}
    for old_name, new_name in zip(original_names, normalized_names):
        if new_name in seen:
            to_drop.append(old_name)
        else:
            seen.add(new_name)
            rename_map[old_name] = new_name

    if to_drop:
        raw.drop_channels(to_drop)
    raw.rename_channels(rename_map)
    return raw

def align_channels(
    raw: mne.io.BaseRaw,
    target_channels: Sequence[str],
    policy: str = "strict",
) -> Tuple[np.ndarray, Dict[str, Any]]:
    normalized_targets = [normalize_channel_name(ch) for ch in target_channels]

    # Fetch full EDF matrix once to avoid repeated disk IO per channel.
    raw_data = raw.get_data()
    existing_names = [normalize_channel_name(ch) for ch in raw.ch_names]
    name_to_idx = {name: idx for idx, name in enumerate(existing_names)}

    n_ch = len(normalized_targets)
    missing_channels = []
    reversed_channels = []
    n_times = raw_data.shape[1]

    # Pre-allocate output matrix instead of list + vstack
    data = np.zeros((n_ch, n_times), dtype=raw_data.dtype)

    for i, target in enumerate(normalized_targets):
        idx = name_to_idx.get(target)
        if idx is not None:
            data[i] = raw_data[idx]
            continue

        if "-" in target:
            reverse_target = "-".join(target.split("-")[::-1])
            reverse_idx = name_to_idx.get(reverse_target)
            if reverse_idx is not None:
                np.negative(raw_data[reverse_idx], out=data[i])
                reversed_channels.append(target)
                continue

        if policy == "zero_fill":
            # data[i] is already zeros
            missing_channels.append(target)
        else:
            raise ValueError(f"Missing target channel: {target}")

    info = {
        "missing_channels": missing_channels,
        "missing_count": len(missing_channels),
        "reversed_channels": reversed_channels,
    }
    return data, info

def build_epoch_labels(
    n_epochs: int,
    epoch_len_s: int,
    seizure_intervals: Sequence[Tuple[int, int]],
) -> np.ndarray:
    """Vectorized: broadcast over epochs instead of Python for-loop."""
    labels = np.zeros(n_epochs, dtype=np.int8)
    if not seizure_intervals:
        return labels
    epoch_starts = np.arange(n_epochs) * epoch_len_s
    epoch_ends = epoch_starts + epoch_len_s
    for sz_start, sz_end in seizure_intervals:
        overlap = (epoch_starts < sz_end) & (sz_start < epoch_ends)
        labels[overlap] = 1
    return labels

def get_band_tuples(cfg: ExperimentConfig) -> List[Tuple[str, Tuple[int, int]]]:
    edges = cfg.feature.band_edges_hz
    bands = []
    for low, high in zip(edges[:-1], edges[1:]):
        bands.append((f"{low}-{high}Hz", (int(low), int(high))))
    return bands

def get_synchrony_index_pairs(cfg: ExperimentConfig) -> List[Tuple[int, int]]:
    channels_norm = tuple(normalize_channel_name(ch) for ch in cfg.channels)
    pairs_norm = tuple((normalize_channel_name(a), normalize_channel_name(b)) for a, b in cfg.feature.synchrony_pairs_names)
    key = (channels_norm, pairs_norm)

    cached = _SYNC_INDEX_CACHE.get(key)
    if cached is not None:
        return cached

    channel_to_idx = {ch: i for i, ch in enumerate(channels_norm)}
    pairs = []
    for left_name, right_name in pairs_norm:
        pairs.append((channel_to_idx[left_name], channel_to_idx[right_name]))

    _SYNC_INDEX_CACHE[key] = pairs
    return pairs

def bandpass_filter_multich(
    data: np.ndarray,
    fs: int,
    lowcut: float,
    highcut: float,
    method: str = "butter_sos",
    butter_order: int = 4,
) -> np.ndarray:
    method = str(method).lower()

    if method == "butter_sos":
        key = (int(fs), float(lowcut), float(highcut), int(butter_order))
        sos = _SOS_CACHE.get(key)
        if sos is None:
            nyquist = 0.5 * fs
            if highcut >= nyquist:
                raise ValueError(f"highcut={highcut} must be < Nyquist {nyquist}.")
            sos = butter(int(butter_order), [lowcut / nyquist, highcut / nyquist], btype="bandpass", output="sos")
            _SOS_CACHE[key] = sos
        return sosfiltfilt(sos, data, axis=1)

    if method == "fir_zero":
        return mne.filter.filter_data(
            data=data,
            sfreq=float(fs),
            l_freq=float(lowcut),
            h_freq=float(highcut),
            method="fir",
            phase="zero",
            verbose=False,
        )

    raise ValueError(f"Unsupported bandpass method: {method}")

def _get_band_masks(fs: int, epoch_samples: int, band_edges: Sequence[int]) -> List[np.ndarray]:
    edges = tuple(int(x) for x in band_edges)
    key = (int(fs), int(epoch_samples), edges)
    cached = _BAND_MASK_CACHE.get(key)
    if cached is not None:
        return cached

    freqs = np.fft.rfftfreq(epoch_samples, d=1.0 / fs)
    masks = []
    for idx, (low, high) in enumerate(zip(edges[:-1], edges[1:])):
        is_last = idx == len(edges) - 2
        if is_last:
            mask = (freqs >= low) & (freqs <= high)
        else:
            mask = (freqs >= low) & (freqs < high)
        masks.append(mask)

    _BAND_MASK_CACHE[key] = masks
    return masks

def extract_base_features_for_file(
    data_bp: np.ndarray,
    fs: int,
    cfg: ExperimentConfig,
) -> Tuple[np.ndarray, np.ndarray]:
    epoch_len_s = cfg.feature.epoch_len_s
    epoch_samples = epoch_len_s * fs
    n_epochs = data_bp.shape[1] // epoch_samples

    if n_epochs == 0:
        return np.empty((0, 0), dtype=float), np.empty((0,), dtype=int)

    usable = data_bp[:, : n_epochs * epoch_samples]
    epochs = usable.reshape(data_bp.shape[0], n_epochs, epoch_samples).transpose(1, 0, 2)
    # Center once, reuse for both FFT and sync (optimization #2)
    epochs_centered = epochs - epochs.mean(axis=2, keepdims=True)

    fft_vals = np.fft.rfft(epochs_centered, axis=-1)
    # One-step power: avoid sqrt inside np.abs then squaring back (optimization #5)
    power = fft_vals.real ** 2 + fft_vals.imag ** 2

    band_masks = _get_band_masks(fs, epoch_samples, cfg.feature.band_edges_hz)
    band_features = [power[:, :, mask].sum(axis=-1) for mask in band_masks]

    band_cube = np.stack(band_features, axis=-1)
    band_flat = band_cube.reshape(n_epochs, -1)

    sync_values = []
    for idx_a, idx_b in get_synchrony_index_pairs(cfg):
        sig_a = epochs_centered[:, idx_a, :]
        sig_b = epochs_centered[:, idx_b, :]

        numerator = np.sum(sig_a * sig_b, axis=1)
        denominator = np.sqrt(np.sum(sig_a ** 2, axis=1) * np.sum(sig_b ** 2, axis=1))
        corr = np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0)
        corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)
        sync_values.append(corr)

    sync_matrix = np.stack(sync_values, axis=1) if sync_values else np.empty((n_epochs, 0), dtype=float)
    X_base = np.hstack([band_flat, sync_matrix]).astype(np.float32)

    return X_base, np.arange(n_epochs, dtype=int)

def temporal_stack_features(
    X_base: np.ndarray,
    y: np.ndarray,
    history_epochs: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """Pre-allocate output matrix instead of vstack + hstack (optimization #4)."""
    if X_base.shape[0] != len(y):
        raise ValueError("X_base and y length mismatch.")

    n_epochs, base_dim = X_base.shape
    total_dim = base_dim * (history_epochs + 1)
    X_stacked = np.zeros((n_epochs, total_dim), dtype=np.float32)

    col = 0
    for lag in range(history_epochs, -1, -1):
        dst = X_stacked[:, col : col + base_dim]
        if lag == 0:
            dst[:] = X_base
        else:
            dst[lag:] = X_base[:-lag]
        col += base_dim

    return X_stacked, y.copy()

def build_base_feature_names(cfg: ExperimentConfig) -> List[str]:
    """Cached: result depends only on cfg (optimization #9)."""
    obj_id = id(cfg)
    cached = _BASE_FEATURE_NAMES_CACHE.get(obj_id)
    if cached is not None:
        return cached
    names = []
    bands = get_band_tuples(cfg)

    for ch in cfg.channels:
        for band_name, _ in bands:
            names.append(f"{ch} [{band_name}]")

    for idx_a, idx_b in get_synchrony_index_pairs(cfg):
        names.append(f"Sync: {cfg.channels[idx_a]} & {cfg.channels[idx_b]}")

    _BASE_FEATURE_NAMES_CACHE[obj_id] = names
    return names

def build_stacked_feature_names(cfg: ExperimentConfig) -> List[str]:
    """Cached: result depends only on cfg (optimization #9)."""
    obj_id = id(cfg)
    cached = _STACKED_FEATURE_NAMES_CACHE.get(obj_id)
    if cached is not None:
        return cached
    base_names = build_base_feature_names(cfg)
    names = []
    history = cfg.feature.history_epochs

    for lag in range(history, 0, -1):
        for name in base_names:
            names.append(f"{name} @ t-{lag}")
    for name in base_names:
        names.append(f"{name} @ t")

    _STACKED_FEATURE_NAMES_CACHE[obj_id] = names
    return names

def apply_duration_constraint(binary_preds: np.ndarray, min_epochs: int = 3) -> np.ndarray:
    cleaned = np.asarray(binary_preds, dtype=np.int8).copy()
    if cleaned.size == 0 or min_epochs <= 1:
        return cleaned

    padded = np.pad(cleaned, (1, 1), mode="constant", constant_values=0)
    diff = np.diff(padded)
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]

    short_runs = (ends - starts) < min_epochs
    for run_start, run_end in zip(starts[short_runs], ends[short_runs]):
        cleaned[run_start:run_end] = 0

    return cleaned

def count_events(labels: np.ndarray) -> int:
    labels = np.asarray(labels)
    if labels.size == 0:
        return 0
    return int((labels[0] == 1) + np.sum((labels[1:] == 1) & (labels[:-1] == 0)))

def extract_binary_runs(labels: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    labels = np.asarray(labels, dtype=np.int8)
    if labels.size == 0:
        empty = np.empty((0,), dtype=int)
        return empty, empty

    padded = np.pad(labels, (1, 1), mode="constant", constant_values=0)
    diff = np.diff(padded)
    starts = np.flatnonzero(diff == 1).astype(int)
    ends = np.flatnonzero(diff == -1).astype(int)
    return starts, ends

def compute_event_metrics(
    y_true: np.ndarray,
    y_pred_binary: np.ndarray,
    epoch_len_s: int,
) -> Dict[str, float]:
    y_true = np.asarray(y_true, dtype=np.int8)
    y_pred_binary = np.asarray(y_pred_binary, dtype=np.int8)

    true_starts, true_ends = extract_binary_runs(y_true)
    total_events = int(len(true_starts))
    detected_events = 0
    delays_s = []

    for event_start, event_end in zip(true_starts, true_ends):
        pred_positions = np.flatnonzero(y_pred_binary[event_start:event_end] == 1)
        if pred_positions.size > 0:
            detected_events += 1
            delays_s.append(int(pred_positions[0]) * epoch_len_s)

    false_alarm_mask = ((y_pred_binary == 1) & (y_true == 0)).astype(np.int8)
    false_alarm_events = int(len(extract_binary_runs(false_alarm_mask)[0]))

    total_hours = len(y_true) * epoch_len_s / 3600.0
    sensitivity = detected_events / total_events if total_events > 0 else np.nan
    far_per_hour = false_alarm_events / total_hours if total_hours > 0 else np.nan

    return {
        "events": float(total_events),
        "detected_events": float(detected_events),
        "sensitivity": float(sensitivity) if not np.isnan(sensitivity) else np.nan,
        "false_alarm_events": float(false_alarm_events),
        "far_per_hour": float(far_per_hour) if not np.isnan(far_per_hour) else np.nan,
        "mean_delay_s": float(np.mean(delays_s)) if delays_s else np.nan,
        "median_delay_s": float(np.median(delays_s)) if delays_s else np.nan,
        "hours": float(total_hours),
    }

def sample_training_rows(
    X: np.ndarray,
    y: np.ndarray,
    cfg: ExperimentConfig,
    rng: np.random.Generator,
) -> Tuple[np.ndarray, np.ndarray]:
    """Optimized: single index array avoids multiple data copies (optimization #12)."""
    pos_idx = np.flatnonzero(y == 1)
    neg_idx = np.flatnonzero(y == 0)

    if len(pos_idx) == 0:
        return X.copy(), y.copy()

    target_neg = max(cfg.eval.min_neg_samples, len(pos_idx) * cfg.eval.neg_to_pos_ratio)
    target_neg = min(target_neg, len(neg_idx))

    if target_neg < len(neg_idx):
        neg_idx = rng.choice(neg_idx, size=target_neg, replace=False)

    combined = np.concatenate([pos_idx, neg_idx])
    rng.shuffle(combined)
    return X[combined], y[combined]

def choose_threshold_from_validation(
    y_true: np.ndarray,
    y_score: np.ndarray,
    cfg: ExperimentConfig,
) -> Dict[str, float]:
    best = None
    fallback = None

    threshold_grid = cfg.eval.threshold_grid
    min_duration = cfg.eval.min_duration_epochs
    epoch_len_s = cfg.feature.epoch_len_s
    min_sens = cfg.eval.min_acceptable_sensitivity

    for thr in threshold_grid:
        y_pred = (y_score >= thr).astype(np.int8)
        y_pred = apply_duration_constraint(y_pred, min_duration)
        metrics = compute_event_metrics(y_true, y_pred, epoch_len_s)

        row = {
            "threshold": float(thr),
            "sensitivity": metrics["sensitivity"],
            "far_per_hour": metrics["far_per_hour"],
            "median_delay_s": metrics["median_delay_s"],
        }

        # Optimization #11: helper to avoid repeated np.nan_to_num calls
        _s = row["sensitivity"] if not np.isnan(row["sensitivity"]) else -1.0
        _f = row["far_per_hour"] if not np.isnan(row["far_per_hour"]) else float("inf")
        _d = row["median_delay_s"] if not np.isnan(row["median_delay_s"]) else float("inf")
        row_rank = (-_s, _f, _d)

        if fallback is None:
            fallback = row
            fallback_rank = row_rank
        else:
            if row_rank < fallback_rank:
                fallback = row
                fallback_rank = row_rank

        if (
            not np.isnan(metrics["sensitivity"])
            and metrics["sensitivity"] >= min_sens
        ):
            best_row_rank = (_f, _d, -_s)
            if best is None:
                best = row
                best_rank = best_row_rank
            else:
                if best_row_rank < best_rank:
                    best = row
                    best_rank = best_row_rank

    return best if best is not None else fallback

def split_inner_validation_files(
    train_seizure_files: List[str],
    train_bg_files: List[str],
    seed: int,
) -> Tuple[List[str], List[str], List[str], List[str]]:
    rng = np.random.default_rng(seed)

    if len(train_seizure_files) >= 2:
        shuffled_seizures = train_seizure_files.copy()
        rng.shuffle(shuffled_seizures)
        val_seizure_files = [shuffled_seizures[0]]
        inner_train_seizure_files = shuffled_seizures[1:]
    else:
        val_seizure_files = []
        inner_train_seizure_files = train_seizure_files.copy()

    shuffled_bg = train_bg_files.copy()
    rng.shuffle(shuffled_bg)
    n_val_bg = max(1, len(shuffled_bg) // max(2, len(train_seizure_files) + 1)) if len(shuffled_bg) > 0 else 0
    val_bg_files = shuffled_bg[:n_val_bg]
    inner_train_bg_files = shuffled_bg[n_val_bg:]

    return inner_train_seizure_files, inner_train_bg_files, val_seizure_files, val_bg_files

def build_patient_cache(cfg: ExperimentConfig, patient_id: str, overwrite: bool = False) -> Path:
    patient_dir = Path(cfg.data_root) / patient_id
    if not patient_dir.exists():
        raise FileNotFoundError(f"找不到病人目录: {patient_dir}")

    cache_path = get_patient_cache_path(cfg, patient_id)
    if cache_path.exists() and not overwrite:
        print(f"[跳过] {patient_id}: 发现同配置缓存 -> {cache_path.name}")
        return cache_path

    summary_path = patient_dir / f"{patient_id}-summary.txt"
    seizure_dict = parse_summary_to_dict(summary_path)

    file_payload = {}
    processed_files = 0
    skipped_files = 0

    for edf_path in sorted(patient_dir.glob("*.edf")):
        raw = None
        try:
            raw = mne.io.read_raw_edf(edf_path, preload=False, verbose=False)
            raw = deduplicate_and_normalize_raw(raw)

            aligned_data, align_info = align_channels(
                raw=raw,
                target_channels=cfg.channels,
                policy=cfg.feature.channel_missing_policy,
            )

            if cfg.feature.scale_to_uV:
                aligned_data = aligned_data * 1e6

            fs = int(raw.info["sfreq"])
            data_bp = bandpass_filter_multich(
                aligned_data,
                fs=fs,
                lowcut=cfg.feature.bandpass_low_hz,
                highcut=cfg.feature.bandpass_high_hz,
                method=cfg.feature.bandpass_method,
                butter_order=cfg.feature.butter_order,
            )

            X_base, kept_epoch_indices = extract_base_features_for_file(data_bp, fs, cfg)
            if X_base.size == 0:
                skipped_files += 1
                continue

            seizure_intervals = seizure_dict.get(edf_path.name, [])
            y_base = build_epoch_labels(
                n_epochs=len(kept_epoch_indices),
                epoch_len_s=cfg.feature.epoch_len_s,
                seizure_intervals=seizure_intervals,
            )

            X_stacked, y_stacked = temporal_stack_features(
                X_base=X_base,
                y=y_base,
                history_epochs=cfg.feature.history_epochs,
            )

            file_payload[edf_path.name] = {
                "X": X_stacked.astype(np.float32),
                "y": y_stacked.astype(np.int8),
                "has_seizure": bool(len(seizure_intervals) > 0),
                "has_positive_epoch": bool(np.any(y_stacked == 1)),
                "fs": fs,
                "n_epochs": int(len(y_stacked)),
                "missing_channels": align_info["missing_channels"],
                "missing_count": align_info["missing_count"],
                "reversed_channels": align_info["reversed_channels"],
            }

            processed_files += 1

        except Exception as exc:
            skipped_files += 1
            print(f"[警告] {patient_id} / {edf_path.name} 跳过，原因: {exc}")
        finally:
            if raw is not None:
                raw.close()

    payload = {
        "meta": {
            "patient_id": patient_id,
            "config_hash": config_to_hash(cfg),
            "base_feature_dim": len(build_base_feature_names(cfg)),
            "stacked_feature_dim": len(build_stacked_feature_names(cfg)),
            "channel_missing_policy": cfg.feature.channel_missing_policy,
            "history_epochs": cfg.feature.history_epochs,
            "epoch_len_s": cfg.feature.epoch_len_s,
            "cache_schema_version": CACHE_SCHEMA_VERSION,
            "processed_files": processed_files,
            "skipped_files": skipped_files,
        },
        "files": file_payload,
    }

    ensure_dir(cache_path.parent)
    joblib.dump(payload, cache_path)
    print(f"[完成] {patient_id}: processed={processed_files}, skipped={skipped_files}, cache={cache_path.name}")
    return cache_path

def build_all_caches(cfg: ExperimentConfig, overwrite: bool = False, n_jobs: int = 1) -> List[Path]:
    if not Path(cfg.data_root).exists():
        raise FileNotFoundError(
            f"Current data_root does not exist: {cfg.data_root}\n"
            "Please set CFG.data_root to your local CHB-MIT directory."
        )

    n_jobs = int(max(1, n_jobs))
    patient_ids = list(cfg.eval.patient_ids)

    if n_jobs == 1:
        cache_paths = []
        for patient_id in patient_ids:
            cache_paths.append(build_patient_cache(cfg, patient_id, overwrite=overwrite))
            gc.collect()
        return cache_paths

    print(f"Building caches in parallel: n_jobs={n_jobs}, patients={len(patient_ids)}")
    cache_paths = joblib.Parallel(n_jobs=n_jobs, backend="loky")(
        joblib.delayed(build_patient_cache)(cfg, patient_id, overwrite=overwrite)
        for patient_id in patient_ids
    )
    return list(cache_paths)

def load_patient_cache(cfg: ExperimentConfig, patient_id: str) -> Dict[str, Any]:
    cache_path = get_patient_cache_path(cfg, patient_id)
    if not cache_path.exists():
        raise FileNotFoundError(f"找不到缓存文件: {cache_path}")

    payload = joblib.load(cache_path)
    meta = payload.get("meta", {})
    files = payload.get("files", {})

    expected_hash = config_to_hash(cfg)
    if meta.get("config_hash") != expected_hash:
        raise ValueError(
            f"{patient_id} 的缓存配置与当前 notebook 不一致。\n"
            f"缓存 hash = {meta.get('config_hash')}\n"
            f"当前 hash = {expected_hash}\n"
            "请重新构建缓存。"
        )

    if not isinstance(files, dict):
        raise ValueError(f"{patient_id} 的缓存结构异常：缺少 files 字段。")

    return payload

def load_all_caches(cfg: ExperimentConfig) -> Dict[str, Dict[str, Any]]:
    caches = {}
    for patient_id in cfg.eval.patient_ids:
        cache_path = get_patient_cache_path(cfg, patient_id)
        if cache_path.exists():
            caches[patient_id] = load_patient_cache(cfg, patient_id)
    return caches

def summarize_caches(caches: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for patient_id, payload in caches.items():
        files = payload["files"]
        n_files = len(files)
        n_seizure_files = sum(int(d["has_seizure"]) for d in files.values())
        n_positive_epoch_files = sum(int(d.get("has_positive_epoch", d["has_seizure"])) for d in files.values())
        n_epochs = sum(int(d["n_epochs"]) for d in files.values())
        rows.append(
            {
                "Patient": patient_id,
                "Files": n_files,
                "Seizure_Files": n_seizure_files,
                "Positive_Epoch_Files": n_positive_epoch_files,
                "Epochs": n_epochs,
                "Feature_Dim": payload["meta"]["stacked_feature_dim"],
            }
        )
    return pd.DataFrame(rows).sort_values("Patient").reset_index(drop=True)

def make_model(model_name: str, cfg: ExperimentConfig, scale_pos_weight: float = 1.0):
    if model_name == "svm_rbf":
        return Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "clf",
                    SVC(
                        kernel="rbf",
                        C=cfg.eval.svm_c,
                        gamma=cfg.eval.svm_gamma,
                        probability=True,
                        class_weight="balanced",
                        random_state=cfg.eval.random_state,
                    ),
                ),
            ]
        )

    if model_name == "random_forest":
        return RandomForestClassifier(
            n_estimators=cfg.eval.rf_n_estimators,
            max_depth=cfg.eval.rf_max_depth,
            min_samples_leaf=cfg.eval.rf_min_samples_leaf,
            max_features=cfg.eval.rf_max_features,
            class_weight="balanced_subsample",
            n_jobs=cfg.eval.rf_n_jobs,
            random_state=cfg.eval.random_state,
        )

    if model_name == "xgboost":
        return XGBClassifier(
            n_estimators=cfg.eval.xgb_n_estimators,
            max_depth=cfg.eval.xgb_max_depth,
            learning_rate=cfg.eval.xgb_learning_rate,
            subsample=cfg.eval.xgb_subsample,
            colsample_bytree=cfg.eval.xgb_colsample_bytree,
            reg_lambda=cfg.eval.xgb_reg_lambda,
            min_child_weight=cfg.eval.xgb_min_child_weight,
            gamma=cfg.eval.xgb_gamma,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            tree_method=cfg.eval.xgb_tree_method,
            n_jobs=cfg.eval.xgb_n_jobs,
            random_state=cfg.eval.random_state,
        )

    raise ValueError(f"Unsupported model_name: {model_name}")

def compute_scale_pos_weight(y: np.ndarray) -> float:
    y = np.asarray(y)
    pos = int(np.sum(y == 1))
    neg = int(np.sum(y == 0))
    return float(neg / max(1, pos))

def build_patient_matrix_index(
    patient_payload: Dict[str, Any],
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Tuple[int, int]]]:
    cache_key = "_matrix_index_cache"
    cached = patient_payload.get(cache_key)
    if cached is not None:
        return cached["X_all"], cached["y_all"], cached["file_row_spans"]

    file_payload = patient_payload["files"]
    ordered_files = sorted(file_payload.keys())

    X_blocks = []
    y_blocks = []
    file_row_spans = {}
    row_start = 0

    for file_name in ordered_files:
        item = file_payload[file_name]
        X_block = np.asarray(item["X"], dtype=np.float32)
        y_block = np.asarray(item["y"], dtype=np.int8)

        row_end = row_start + len(y_block)
        file_row_spans[file_name] = (row_start, row_end)

        X_blocks.append(X_block)
        y_blocks.append(y_block)
        row_start = row_end

    if len(X_blocks) == 0:
        X_all = np.empty((0, 0), dtype=np.float32)
        y_all = np.empty((0,), dtype=np.int8)
    else:
        X_all = np.vstack(X_blocks).astype(np.float32, copy=False)
        y_all = np.concatenate(y_blocks).astype(np.int8, copy=False)

    patient_payload[cache_key] = {
        "X_all": X_all,
        "y_all": y_all,
        "file_row_spans": file_row_spans,
    }
    return X_all, y_all, file_row_spans

def collect_rows_from_matrix_index(
    X_all: np.ndarray,
    y_all: np.ndarray,
    file_row_spans: Dict[str, Tuple[int, int]],
    file_names: Sequence[str],
    feature_indices: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    if len(file_names) == 0:
        feature_dim = X_all.shape[1] if feature_indices is None else int(len(feature_indices))
        return np.empty((0, feature_dim), dtype=np.float32), np.empty((0,), dtype=np.int8)

    blocks_X = []
    blocks_y = []
    for file_name in file_names:
        if file_name not in file_row_spans:
            raise KeyError(f"Unknown file in row index: {file_name}")

        start, end = file_row_spans[file_name]
        X_block = X_all[start:end]
        if feature_indices is not None:
            X_block = X_block[:, feature_indices]
        blocks_X.append(X_block)
        blocks_y.append(y_all[start:end])

    if len(blocks_X) == 1:
        return blocks_X[0], blocks_y[0]

    return np.concatenate(blocks_X, axis=0), np.concatenate(blocks_y, axis=0)

def collect_rows_from_files(
    patient_payload: Dict[str, Any],
    file_names: Sequence[str],
    feature_indices: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Convenience wrapper; callers with existing matrix index should use
    collect_rows_from_matrix_index directly to avoid redundant lookups (optimization #20)."""
    X_all, y_all, file_row_spans = build_patient_matrix_index(patient_payload)
    return collect_rows_from_matrix_index(
        X_all=X_all,
        y_all=y_all,
        file_row_spans=file_row_spans,
        file_names=file_names,
        feature_indices=feature_indices,
    )

def topk_feature_cache_hash(cfg: ExperimentConfig) -> str:
    payload = {
        "feature": make_json_safe(asdict(cfg.feature)),
        "selector_n_estimators": cfg.eval.selector_n_estimators,
        "selector_max_depth": cfg.eval.selector_max_depth,
        "rf_max_features": cfg.eval.rf_max_features,
        "rf_min_samples_leaf": cfg.eval.rf_min_samples_leaf,
        "xgb_tree_method": cfg.eval.xgb_tree_method,
        "xgb_n_jobs": cfg.eval.xgb_n_jobs,
        "random_state": cfg.eval.random_state,
    }
    payload_str = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return joblib.hash(payload_str)

def select_top_k_features_tree(
    X_train: np.ndarray,
    y_train: np.ndarray,
    top_k: int,
    cfg: ExperimentConfig,
    selector_model_name: str = "random_forest",
) -> np.ndarray:
    if X_train.shape[1] <= top_k:
        return np.arange(X_train.shape[1], dtype=int)

    if selector_model_name == "xgboost":
        scale_pos_weight = compute_scale_pos_weight(y_train)
        selector = XGBClassifier(
            n_estimators=cfg.eval.selector_n_estimators,
            max_depth=cfg.eval.selector_max_depth,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            tree_method=cfg.eval.xgb_tree_method,
            n_jobs=cfg.eval.xgb_n_jobs,
            random_state=cfg.eval.random_state,
        )
    else:
        selector = RandomForestClassifier(
            n_estimators=cfg.eval.selector_n_estimators,
            max_depth=cfg.eval.selector_max_depth,
            min_samples_leaf=cfg.eval.rf_min_samples_leaf,
            max_features=cfg.eval.rf_max_features,
            class_weight="balanced_subsample",
            n_jobs=cfg.eval.rf_n_jobs,
            random_state=cfg.eval.random_state,
        )

    selector.fit(X_train, y_train)
    importances = selector.feature_importances_
    top_idx = np.argsort(importances)[-top_k:]
    return np.sort(top_idx)

def evaluate_patient_loso(
    patient_payload: Dict[str, Any],
    cfg: ExperimentConfig,
    model_name: str = "xgboost",
    top_k: Optional[int] = None,
    patient_seed_offset: int = 0,
    fold_topk_cache: Optional[Dict[Tuple[Any, ...], np.ndarray]] = None,
) -> Dict[str, Any]:
    patient_id = patient_payload["meta"]["patient_id"]
    file_payload = patient_payload["files"]
    seizure_files = sorted([f for f, d in file_payload.items() if d["has_seizure"]])
    bg_files = sorted([f for f, d in file_payload.items() if not d["has_seizure"]])

    if len(seizure_files) < 2:
        raise ValueError("Seizure file count < 2; cannot run LOSO.")

    X_all, y_all, file_row_spans = build_patient_matrix_index(patient_payload)
    feature_cfg_hash = topk_feature_cache_hash(cfg)

    rng = np.random.default_rng(cfg.eval.random_state + patient_seed_offset)
    shuffled_bg = bg_files.copy()
    rng.shuffle(shuffled_bg)
    bg_chunks = np.array_split(shuffled_bg, len(seizure_files))

    fold_rows = []
    all_y_true = []
    all_y_pred = []
    all_y_score = []
    all_selected_features = []
    topk_cache_hits = 0
    topk_cache_misses = 0

    for outer_idx, test_seizure_file in enumerate(seizure_files):
        outer_train_seizure_files = seizure_files[:outer_idx] + seizure_files[outer_idx + 1 :]
        outer_test_bg_files = list(bg_chunks[outer_idx])
        outer_test_bg_set = set(outer_test_bg_files)
        outer_train_bg_files = [f for f in bg_files if f not in outer_test_bg_set]

        inner_train_seizure_files, inner_train_bg_files, val_seizure_files, val_bg_files = split_inner_validation_files(
            outer_train_seizure_files,
            outer_train_bg_files,
            seed=cfg.eval.random_state + patient_seed_offset + outer_idx,
        )

        inner_train_files = inner_train_seizure_files + inner_train_bg_files
        X_inner_raw, y_inner_raw = collect_rows_from_matrix_index(
            X_all=X_all,
            y_all=y_all,
            file_row_spans=file_row_spans,
            file_names=inner_train_files,
            feature_indices=None,
        )
        if len(y_inner_raw) == 0:
            raise ValueError("No inner-train samples available in this fold.")

        feature_indices = None
        if top_k is not None:
            selector_seed = cfg.eval.random_state + 1000 + outer_idx
            cache_key = (
                patient_id,
                feature_cfg_hash,
                int(top_k),
                int(outer_idx),
                tuple(inner_train_files),
                int(selector_seed),
            )

            if fold_topk_cache is not None and cache_key in fold_topk_cache:
                feature_indices = fold_topk_cache[cache_key]
                topk_cache_hits += 1
            else:
                selector_rng = np.random.default_rng(selector_seed)
                X_selector, y_selector = sample_training_rows(X_inner_raw, y_inner_raw, cfg, selector_rng)
                selector_model_name = model_name if model_name in {"random_forest", "xgboost"} else "random_forest"
                feature_indices = select_top_k_features_tree(
                    X_selector,
                    y_selector,
                    top_k=top_k,
                    cfg=cfg,
                    selector_model_name=selector_model_name,
                )
                if fold_topk_cache is not None:
                    fold_topk_cache[cache_key] = feature_indices
                topk_cache_misses += 1

            all_selected_features.append(feature_indices)

        use_fixed_threshold = bool(getattr(cfg.eval, "fixed_threshold_mode", False))
        if use_fixed_threshold:
            threshold = float(getattr(cfg.eval, "fixed_threshold_value", cfg.eval.default_threshold))
        else:
            threshold = cfg.eval.default_threshold
            if len(val_seizure_files) > 0:
                X_train_inner = X_inner_raw if feature_indices is None else X_inner_raw[:, feature_indices]
                train_rng = np.random.default_rng(cfg.eval.random_state + 2000 + outer_idx)
                X_train_inner, y_train_inner = sample_training_rows(X_train_inner, y_inner_raw, cfg, train_rng)

                inner_model = make_model(
                    model_name,
                    cfg,
                    scale_pos_weight=compute_scale_pos_weight(y_train_inner),
                )
                inner_model.fit(X_train_inner, y_train_inner)

                X_val, y_val = collect_rows_from_matrix_index(
                    X_all=X_all,
                    y_all=y_all,
                    file_row_spans=file_row_spans,
                    file_names=val_seizure_files + val_bg_files,
                    feature_indices=feature_indices,
                )
                val_scores = inner_model.predict_proba(X_val)[:, 1]
                threshold_info = choose_threshold_from_validation(y_val, val_scores, cfg)
                threshold = threshold_info["threshold"]

        X_train_outer, y_train_outer = collect_rows_from_matrix_index(
            X_all=X_all,
            y_all=y_all,
            file_row_spans=file_row_spans,
            file_names=outer_train_seizure_files + outer_train_bg_files,
            feature_indices=feature_indices,
        )
        outer_rng = np.random.default_rng(cfg.eval.random_state + 3000 + outer_idx)
        X_train_outer, y_train_outer = sample_training_rows(X_train_outer, y_train_outer, cfg, outer_rng)

        model = make_model(
            model_name,
            cfg,
            scale_pos_weight=compute_scale_pos_weight(y_train_outer),
        )
        model.fit(X_train_outer, y_train_outer)

        X_test, y_test = collect_rows_from_matrix_index(
            X_all=X_all,
            y_all=y_all,
            file_row_spans=file_row_spans,
            file_names=sorted([test_seizure_file] + outer_test_bg_files),
            feature_indices=feature_indices,
        )
        y_score = model.predict_proba(X_test)[:, 1]
        y_score_smoothed = medfilt(y_score, kernel_size=5)
        y_pred = (y_score_smoothed >= threshold).astype(np.int8)
        y_pred = apply_duration_constraint(y_pred, cfg.eval.min_duration_epochs)

        fold_metrics = compute_event_metrics(y_test, y_pred, cfg.feature.epoch_len_s)
        fold_rows.append(
            {
                "fold": outer_idx,
                "threshold": threshold,
                "test_seizure_file": test_seizure_file,
                "n_test_bg_files": len(outer_test_bg_files),
                "sensitivity": fold_metrics["sensitivity"],
                "far_per_hour": fold_metrics["far_per_hour"],
                "median_delay_s": fold_metrics["median_delay_s"],
            }
        )

        all_y_true.append(y_test)
        all_y_pred.append(y_pred)
        all_y_score.append(y_score_smoothed)

    y_true_cat = np.concatenate(all_y_true)
    y_pred_cat = np.concatenate(all_y_pred)
    y_score_cat = np.concatenate(all_y_score)

    patient_metrics = compute_event_metrics(y_true_cat, y_pred_cat, cfg.feature.epoch_len_s)
    summary = {
        "Patient": patient_id,
        "Model": model_name,
        "TopK": top_k if top_k is not None else -1,
        "Hours": patient_metrics["hours"],
        "True_Seizures": patient_metrics["events"],
        "Sensitivity": patient_metrics["sensitivity"],
        "FAR_per_Hour": patient_metrics["far_per_hour"],
        "Mean_Delay_s": patient_metrics["mean_delay_s"],
        "Median_Delay_s": patient_metrics["median_delay_s"],
        "Median_Threshold": float(np.median([row["threshold"] for row in fold_rows])),
    }

    return {
        "summary": summary,
        "folds": pd.DataFrame(fold_rows),
        "y_true": y_true_cat,
        "y_pred": y_pred_cat,
        "y_score": y_score_cat,
        "selected_features": all_selected_features,
        "topk_cache_hits": int(topk_cache_hits),
        "topk_cache_misses": int(topk_cache_misses),
    }

def evaluate_many_patients(
    caches: Dict[str, Dict[str, Any]],
    cfg: ExperimentConfig,
    model_name: str = "xgboost",
    top_k: Optional[int] = None,
    fold_topk_cache: Optional[Dict[Tuple[Any, ...], np.ndarray]] = None,
) -> Dict[str, Any]:
    patient_outputs = {}
    summary_rows = []
    total_cache_hits = 0
    total_cache_misses = 0

    for patient_idx, patient_id in enumerate(cfg.eval.patient_ids):
        if patient_id not in caches:
            continue

        try:
            result = evaluate_patient_loso(
                patient_payload=caches[patient_id],
                cfg=cfg,
                model_name=model_name,
                top_k=top_k,
                patient_seed_offset=patient_idx * 100,
                fold_topk_cache=fold_topk_cache,
            )
            patient_outputs[patient_id] = result
            summary_rows.append(result["summary"])
            total_cache_hits += int(result.get("topk_cache_hits", 0))
            total_cache_misses += int(result.get("topk_cache_misses", 0))
            print(
                f"[{patient_id}] {model_name} | "
                f"Sens={result['summary']['Sensitivity']:.2%} | "
                f"FAR/hr={result['summary']['FAR_per_Hour']:.4f} | "
                f"MedianThr={result['summary']['Median_Threshold']:.3f}"
            )
        except Exception as exc:
            print(f"[警告] {patient_id} 评估失败: {exc}")

    summary_df = pd.DataFrame(summary_rows)
    return {
        "patient_outputs": patient_outputs,
        "summary_df": summary_df,
        "topk_cache_hits": int(total_cache_hits),
        "topk_cache_misses": int(total_cache_misses),
    }

def _safe_float(x, default=0.0):
    """Simplified: single try/except block (optimization #15)."""
    try:
        return float(x) if x is not None and not np.isnan(x) else float(default)
    except (TypeError, ValueError):
        return float(default)

def _aggregate_summary(summary_df: pd.DataFrame) -> Dict[str, float]:
    if summary_df is None or summary_df.empty:
        return {
            "mean_sensitivity": np.nan,
            "median_far_per_hour": np.nan,
            "mean_delay_s": np.nan,
            "patients": 0,
        }
    return {
        "mean_sensitivity": float(summary_df["Sensitivity"].mean()),
        "median_far_per_hour": float(summary_df["FAR_per_Hour"].median()),
        "mean_delay_s": float(summary_df["Mean_Delay_s"].mean()),
        "patients": int(len(summary_df)),
    }

def _priority_sort(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df

    work = df.copy()
    work["_sens"] = work["mean_sensitivity"].apply(lambda v: _safe_float(v, -1.0))
    work["_far"] = work["median_far_per_hour"].apply(lambda v: _safe_float(v, 1e9))
    work["_delay"] = work["mean_delay_s"].apply(lambda v: _safe_float(v, 1e9))

    work = work.sort_values(["_sens", "_far", "_delay"], ascending=[False, True, True]).reset_index(drop=True)
    work["priority_rank"] = np.arange(1, len(work) + 1)
    work = work.drop(columns=["_sens", "_far", "_delay"])
    return work

def _run_rf_eval(
    cfg_variant: ExperimentConfig,
    caches_variant: Dict[str, Dict[str, Any]],
    top_k: int,
    fold_topk_cache: Optional[Dict[Tuple[Any, ...], np.ndarray]] = None,
):
    t0 = time.perf_counter()
    result = evaluate_many_patients(
        caches=caches_variant,
        cfg=cfg_variant,
        model_name="random_forest",
        top_k=top_k,
        fold_topk_cache=fold_topk_cache,
    )
    summary_df = result.get("summary_df", pd.DataFrame())
    agg = _aggregate_summary(summary_df)
    agg["elapsed_s"] = float(time.perf_counter() - t0)
    agg["fold_topk_cache_entries"] = int(len(fold_topk_cache)) if fold_topk_cache is not None else 0
    agg["topk_cache_hits"] = int(result.get("topk_cache_hits", 0))
    agg["topk_cache_misses"] = int(result.get("topk_cache_misses", 0))
    return result, agg

def _build_macro_row(summary_df: pd.DataFrame, model_name: str, top_k: Optional[int]) -> Dict[str, Any]:
    if summary_df is None or summary_df.empty:
        return {
            "Model": model_name,
            "TopK": top_k if top_k is not None else -1,
            "Patients": 0,
            "Sensitivity": np.nan,
            "FAR_per_Hour": np.nan,
            "Mean_Delay_s": np.nan,
            "Median_Delay_s": np.nan,
            "Median_Threshold": np.nan,
        }
    return {
        "Model": model_name,
        "TopK": top_k if top_k is not None else -1,
        "Patients": int(len(summary_df)),
        "Sensitivity": float(summary_df["Sensitivity"].mean()),
        "FAR_per_Hour": float(summary_df["FAR_per_Hour"].median()),
        "Mean_Delay_s": float(summary_df["Mean_Delay_s"].mean()),
        "Median_Delay_s": float(summary_df["Median_Delay_s"].median()),
        "Median_Threshold": float(summary_df["Median_Threshold"].median()),
    }

def _sort_benchmark(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df
    out = df.copy()
    out = out.sort_values(
        ["Sensitivity", "FAR_per_Hour", "Mean_Delay_s"],
        ascending=[False, True, True],
    ).reset_index(drop=True)
    return out

def build_event_detection_matrix(
    result_bundle: Dict[str, Any],
    cfg: ExperimentConfig,
    label: str,
) -> pd.DataFrame:
    patient_outputs = result_bundle.get("patient_outputs", {})

    tp_events = 0.0
    fn_events = 0.0
    fp_events = 0.0
    total_hours = 0.0
    delay_weighted_sum = 0.0
    delay_weight = 0.0

    for _, patient_res in patient_outputs.items():
        metrics = compute_event_metrics(
            patient_res["y_true"],
            patient_res["y_pred"],
            cfg.feature.epoch_len_s,
        )

        events = float(metrics["events"])
        detected = float(metrics["detected_events"])
        false_alarms = float(metrics["false_alarm_events"])
        hours = float(metrics["hours"])

        tp_events += detected
        fn_events += max(0.0, events - detected)
        fp_events += false_alarms
        total_hours += hours

        if (not np.isnan(metrics["mean_delay_s"])) and detected > 0:
            delay_weighted_sum += float(metrics["mean_delay_s"]) * detected
            delay_weight += detected

    sensitivity = tp_events / max(1.0, tp_events + fn_events)
    far_per_hour = fp_events / max(1e-9, total_hours)
    mean_delay_s = delay_weighted_sum / delay_weight if delay_weight > 0 else np.nan

    return pd.DataFrame(
        [
            {
                "Variant": label,
                "TP_events": float(tp_events),
                "FN_events": float(fn_events),
                "FP_events": float(fp_events),
                "Sensitivity": float(sensitivity),
                "FAR_per_Hour": float(far_per_hour),
                "Mean_Delay_s": float(mean_delay_s) if not np.isnan(mean_delay_s) else np.nan,
                "Hours": float(total_hours),
                "Patients": int(len(patient_outputs)),
            }
        ]
    )

def resolve_final_rf_context() -> Tuple[ExperimentConfig, Dict[str, Dict[str, Any]], int, str]:
    if "TUNED_RF_CFG" in globals():
        cfg = copy.deepcopy(TUNED_RF_CFG)
        caches_local = TUNED_CACHES if "TUNED_CACHES" in globals() else load_all_caches(cfg)
        cfg_source = "TUNED_RF_CFG"
    else:
        cfg = copy.deepcopy(CFG)
        caches_local = caches if "caches" in globals() else load_all_caches(cfg)
        cfg_source = "CFG"

    cfg.eval.patient_ids = tuple(f"chb{i:02d}" for i in range(1, 11))
    cfg.eval.fixed_threshold_mode = False
    final_top_k_local = int(cfg.eval.top_k_features)
    return cfg, caches_local, final_top_k_local, cfg_source

def annotate_bars(ax, fmt="{:.3f}", offset=4):
    for patch in ax.patches:
        h = patch.get_height()
        if np.isfinite(h):
            ax.annotate(
                fmt.format(h),
                (patch.get_x() + patch.get_width() / 2, h),
                ha="center",
                va="bottom",
                fontsize=10,
                xytext=(0, offset),
                textcoords="offset points",
            )

def train_patient_bundle(patient_id: str, payload: Dict[str, Any], cfg: ExperimentConfig, threshold: float) -> Dict[str, Any]:
    file_names = list(payload["files"].keys())
    X_full, y_full = collect_rows_from_files(payload, file_names, feature_indices=None)
    if len(y_full) == 0:
        raise ValueError(f"No rows for {patient_id}")

    cache_key = (
        patient_id,
        cfg.feature.history_epochs,
        cfg.feature.bandpass_method,
        cfg.feature.butter_order,
        cfg.eval.top_k_features,
        cfg.eval.rf_n_estimators,
        cfg.eval.rf_max_depth,
        cfg.eval.rf_min_samples_leaf,
        cfg.eval.rf_max_features,
    )

    if cache_key in patient_topk_cache:
        top_idx = patient_topk_cache[cache_key]
    else:
        rng = np.random.default_rng(cfg.eval.random_state)
        X_sel, y_sel = sample_training_rows(X_full, y_full, cfg, rng)
        top_idx = select_top_k_features_tree(
            X_sel,
            y_sel,
            top_k=cfg.eval.top_k_features,
            cfg=cfg,
            selector_model_name="random_forest",
        )
        patient_topk_cache[cache_key] = top_idx

    X_light = X_full[:, top_idx]
    model = make_model("random_forest", cfg)
    model.fit(X_light, y_full)

    return {
        "patient_id": patient_id,
        "model_name": "random_forest",
        "patient_model_family": "random_forest_patient_specific",
        "model": model,
        "top_k_indices": top_idx,
        "feature_names": [all_feature_names[int(i)] for i in top_idx],
        "threshold": float(threshold),
        "requested_top_k": int(final_top_k),
        "input_dim": int(len(top_idx)),
        "train_rows": int(len(y_full)),
        "train_pos": int(np.sum(y_full == 1)),
        "train_neg": int(np.sum(y_full == 0)),
    }

def _md(text: str):
    display(Markdown(text))

def _safe_copy_df(name: str) -> pd.DataFrame:
    obj = globals().get(name, None)
    if isinstance(obj, pd.DataFrame):
        return obj.copy()
    return pd.DataFrame()

def _show_df(title: str, df: pd.DataFrame, note: str = "", round_cols: dict = None):
    _md(f"## {title}")
    if note:
        _md(note)
    if df is None or df.empty:
        print("[Empty table / variable not found]")
        return

    out = df.copy()

    if round_cols:
        for col, digits in round_cols.items():
            if col in out.columns:
                out[col] = pd.to_numeric(out[col], errors="coerce").round(digits)

    display(out)
    print(f"shape = {out.shape}")

def _reorder_cols(df: pd.DataFrame, preferred_cols: list) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    cols_exist = [c for c in preferred_cols if c in df.columns]
    cols_rest = [c for c in df.columns if c not in cols_exist]
    return df[cols_exist + cols_rest].copy()

def _add_metric_rank(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    if {"Sensitivity", "FAR_per_Hour", "Mean_Delay_s"}.issubset(out.columns):
        out = out.sort_values(
            ["Sensitivity", "FAR_per_Hour", "Mean_Delay_s"],
            ascending=[False, True, True]
        ).reset_index(drop=True)
        out.insert(0, "Rank", np.arange(1, len(out) + 1))
    return out

def benchmark_single_epoch_latency(model, X_stream: np.ndarray, n_steps: int = 1000) -> Dict[str, float]:
    n_steps = min(n_steps, len(X_stream))
    timings = []
    for i in range(n_steps):
        sample = X_stream[i : i + 1]
        t0 = time.perf_counter()
        _ = model.predict_proba(sample)
        t1 = time.perf_counter()
        timings.append(t1 - t0)
    timings = np.asarray(timings)
    return {
        "n_steps": int(n_steps),
        "mean_ms": float(np.mean(timings) * 1000.0),
        "median_ms": float(np.median(timings) * 1000.0),
        "p95_ms": float(np.percentile(timings, 95) * 1000.0),
        "fps_estimate": float(1.0 / np.mean(timings)) if np.mean(timings) > 0 else np.nan,
    }

def profile_rf_model(model, input_dim: int) -> Dict[str, float]:
    buffer = io.BytesIO()
    joblib.dump(model, buffer)
    raw_bytes = buffer.getvalue()
    estimators = list(getattr(model, "estimators_", []))
    total_nodes = int(sum(est.tree_.node_count for est in estimators)) if estimators else 0
    total_leaves = int(sum(np.sum(est.tree_.children_left == -1) for est in estimators)) if estimators else 0
    max_depth = int(max(est.tree_.max_depth for est in estimators)) if estimators else 0
    mean_depth = float(np.mean([est.tree_.max_depth for est in estimators])) if estimators else 0.0

    return {
        "input_dim": int(input_dim),
        "memory_mb": float(len(raw_bytes) / (1024.0 * 1024.0)), # Changed to MB for better readability
        "n_trees": int(len(estimators)),
        "total_nodes": int(total_nodes),
        "total_leaves": int(total_leaves),
        "decision_nodes": int(total_nodes - total_leaves),
        "max_tree_depth": int(max_depth),
        "mean_tree_depth": float(mean_depth),
    }

def align_channels_window(
    raw: mne.io.BaseRaw,
    target_channels: Sequence[str],
    start_idx: int,
    stop_idx: int,
    policy: str = "strict",
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Window-based channel alignment with pre-allocated output (optimization #19).
    NOTE: Logic mirrors align_channels(); consider merging in future refactor.
    """
    normalized_targets = [normalize_channel_name(ch) for ch in target_channels]
    existing = {normalize_channel_name(ch): ch for ch in raw.ch_names}

    n_ch = len(normalized_targets)
    n_times = stop_idx - start_idx
    data = np.zeros((n_ch, n_times), dtype=float)
    missing_channels = []
    reversed_channels = []

    for i, target in enumerate(normalized_targets):
        if target in existing:
            data[i] = raw.get_data(picks=[existing[target]], start=start_idx, stop=stop_idx)[0]
            continue

        if "-" in target:
            reverse_target = "-".join(target.split("-")[::-1])
            if reverse_target in existing:
                data[i] = -raw.get_data(picks=[existing[reverse_target]], start=start_idx, stop=stop_idx)[0]
                reversed_channels.append(target)
                continue

        if policy == "zero_fill":
            # data[i] already zeros
            missing_channels.append(target)
        else:
            raise ValueError(f"Missing target channel: {target}")

    info = {
        "missing_channels": missing_channels,
        "missing_count": len(missing_channels),
        "reversed_channels": reversed_channels,
    }
    return data, info

def build_clinical_case_dataframe(
    patient_id: str,
    patient_payload: Dict[str, Any],
    model,
    feature_indices: np.ndarray,
    threshold: float,
    pre_seconds: int = 12,
    post_seconds: int = 14,
) -> Tuple[str, pd.DataFrame, Dict[str, Any]]:
    seizure_files = [
        f for f, d in patient_payload["files"].items()
        if d["has_seizure"] and d.get("has_positive_epoch", False)
    ]
    if not seizure_files:
        seizure_files = [f for f, d in patient_payload["files"].items() if d["has_seizure"]]
    if not seizure_files:
        raise ValueError(f"No seizure file found for {patient_id}.")

    file_name = sorted(seizure_files)[0]
    item = patient_payload["files"][file_name]

    X = item["X"][:, feature_indices]
    y = item["y"].astype(np.int8)

    seizure_positions = np.flatnonzero(y == 1)
    if len(seizure_positions) == 0:
        raise ValueError(f"No positive epochs in {patient_id}/{file_name}.")

    onset_epoch = int(seizure_positions[0])
    _cfg_case = deploy_cfg if "deploy_cfg" in globals() else CFG
    epoch_len_s = _cfg_case.feature.epoch_len_s
    onset_time_s = onset_epoch * epoch_len_s

    pre_epochs = max(1, int(np.ceil(pre_seconds / epoch_len_s)))
    post_epochs = max(1, int(np.ceil(post_seconds / epoch_len_s)))

    start_epoch = max(0, onset_epoch - pre_epochs)
    end_epoch = min(len(y), onset_epoch + post_epochs + 1)

    epoch_indices = np.arange(start_epoch, end_epoch)
    probs = model.predict_proba(X[start_epoch:end_epoch])[:, 1]
    alarms = probs >= threshold

    case_df = pd.DataFrame(
        {
            "epoch_index": epoch_indices,
            "time_s": epoch_indices * epoch_len_s,
            "time_rel_s": (epoch_indices - onset_epoch) * epoch_len_s,
            "y_true": y[start_epoch:end_epoch],
            "prob": probs,
            "alarm": alarms.astype(bool),
        }
    )

    hit_in_seizure = bool(np.any((case_df["y_true"] == 1) & (case_df["alarm"])))
    false_alarm_before = bool(np.any((case_df["time_rel_s"] < 0) & (case_df["alarm"])))
    first_alarm_rel_s = float(case_df.loc[case_df["alarm"], "time_rel_s"].iloc[0]) if np.any(case_df["alarm"]) else np.nan

    metrics = {
        "patient_id": patient_id,
        "file_name": file_name,
        "onset_epoch": onset_epoch,
        "onset_time_s": onset_time_s,
        "threshold": float(threshold),
        "hit_in_seizure": hit_in_seizure,
        "false_alarm_before": false_alarm_before,
        "first_alarm_rel_s": first_alarm_rel_s,
    }
    return file_name, case_df, metrics

def load_filtered_eeg_segment(
    cfg: ExperimentConfig,
    patient_id: str,
    file_name: str,
    start_time_s: float,
    end_time_s: float,
    onset_time_s: float,
    plot_channels: Sequence[str],
) -> Tuple[np.ndarray, np.ndarray, List[str], Dict[str, Any]]:
    edf_path = Path(cfg.data_root) / patient_id / file_name
    if not edf_path.exists():
        raise FileNotFoundError(f"EDF not found: {edf_path}")

    raw = mne.io.read_raw_edf(edf_path, preload=False, verbose=False)
    raw = deduplicate_and_normalize_raw(raw)
    fs = int(raw.info["sfreq"])

    start_idx = max(0, int(start_time_s * fs))
    stop_idx = min(raw.n_times, int(end_time_s * fs))
    if stop_idx <= start_idx:
        raw.close()
        raise ValueError("Invalid EEG window: stop <= start")

    data_window, align_info = align_channels_window(
        raw=raw,
        target_channels=cfg.channels,
        start_idx=start_idx,
        stop_idx=stop_idx,
        policy=cfg.feature.channel_missing_policy,
    )
    raw.close()

    if cfg.feature.scale_to_uV:
        data_window = data_window * 1e6

    data_bp = bandpass_filter_multich(
        data_window,
        fs=fs,
        lowcut=cfg.feature.bandpass_low_hz,
        highcut=cfg.feature.bandpass_high_hz,
        method=cfg.feature.bandpass_method,
        butter_order=cfg.feature.butter_order,
    )

    target_norm = [normalize_channel_name(ch) for ch in cfg.channels]
    plot_indices = []
    plot_names = []
    for ch in plot_channels:
        ch_norm = normalize_channel_name(ch)
        if ch_norm in target_norm:
            plot_indices.append(target_norm.index(ch_norm))
            plot_names.append(ch)

    if len(plot_indices) == 0:
        plot_indices = list(range(min(4, data_bp.shape[0])))
        plot_names = [cfg.channels[idx] for idx in plot_indices]

    eeg_plot = data_bp[plot_indices]
    t_abs = np.arange(eeg_plot.shape[1]) / fs + (start_idx / fs)
    t_rel = t_abs - onset_time_s

    return eeg_plot, t_rel, plot_names, align_info
