import argparse
import hashlib
import json
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import matplotlib.pyplot as plt
import mne
import numpy as np
from scipy.integrate import simpson
from scipy.signal import butter, filtfilt, welch
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


# ==========================================================
# Section 1: Shared data structures and fixed configuration
# ==========================================================


@dataclass
class EpochMetadata:
    """Metadata for one temporally stacked sample."""

    file_name: str
    start_s: float
    end_s: float


DEFAULT_BANDS = {
    "delta": (0.5, 4),
    "theta": (4, 8),
    "alpha": (8, 13),
    "beta": (13, 30),
}


# ==========================================================
# Section 2: Dataset parsing and channel harmonization
# ==========================================================


def parse_summary_to_dict(summary_path: str) -> Dict[str, List[Tuple[float, float]]]:
    """Parse CHB-MIT style summary file into seizure intervals per EDF."""
    with open(summary_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [ln.strip() for ln in f.readlines()]

    seizure_dict: Dict[str, List[Tuple[float, float]]] = {}
    current_file = None
    starts: List[float] = []
    ends: List[float] = []

    def flush() -> None:
        nonlocal current_file, starts, ends
        if current_file is not None:
            seizure_dict[current_file] = list(zip(starts, ends))
        starts, ends = [], []

    for line in lines:
        m_file = re.match(r"File Name:\s*(.*)", line)
        if m_file:
            flush()
            current_file = m_file.group(1).strip()
            continue

        m_s = re.match(r"Seizure Start Time:\s*(\d+)\s*seconds", line)
        m_e = re.match(r"Seizure End Time:\s*(\d+)\s*seconds", line)
        if m_s and current_file is not None:
            starts.append(float(m_s.group(1)))
        if m_e and current_file is not None:
            ends.append(float(m_e.group(1)))

    flush()
    return seizure_dict


def list_edf_files(folder: str) -> List[str]:
    edf_paths = sorted([os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".edf")])
    if not edf_paths:
        raise FileNotFoundError(f"No EDF files found in: {folder}")
    return edf_paths


def normalize_channel_names(raw: mne.io.BaseRaw) -> None:
    """Normalize known channel naming inconsistencies."""
    if "T8-P8-0" in raw.ch_names and "T8-P8" not in raw.ch_names:
        mne.rename_channels(raw.info, {"T8-P8-0": "T8-P8"})


def find_common_channels(patient_dirs: Sequence[str]) -> List[str]:
    """Find common channel set across all provided patients/files."""
    common: Iterable[str] | None = None
    for patient_dir in patient_dirs:
        for path in list_edf_files(patient_dir):
            raw = mne.io.read_raw_edf(path, preload=False, verbose=False)
            normalize_channel_names(raw)
            channels = set(raw.ch_names)
            raw.close()
            if common is None:
                common = channels
            else:
                common = set(common).intersection(channels)
    if not common:
        raise ValueError("No common channels across selected patients.")
    return sorted(common)


# ==========================================================
# Section 3: Signal segmentation and feature engineering
# ==========================================================


def bandpass_filter_multich(data: np.ndarray, fs: float, l_freq: float, h_freq: float, order: int = 4) -> np.ndarray:
    nyq = 0.5 * fs
    low = l_freq / nyq
    high = h_freq / nyq
    b, a = butter(order, [low, high], btype="band")
    return filtfilt(b, a, data, axis=-1)


def segment_eeg_into_epochs(eeg: np.ndarray, sfreq: float, epoch_len_s: float) -> Dict[str, object]:
    epoch_len_samples = int(epoch_len_s * sfreq)
    n_channels, n_samples = eeg.shape
    n_epochs = n_samples // epoch_len_samples
    trimmed = eeg[:, : n_epochs * epoch_len_samples]
    epochs = trimmed.reshape(n_channels, n_epochs, epoch_len_samples).transpose(1, 0, 2)

    start_samples = np.arange(n_epochs) * epoch_len_samples
    end_samples = start_samples + epoch_len_samples

    return {
        "epochs": epochs,
        "sfreq": sfreq,
        "epoch_len_s": epoch_len_s,
        "epoch_start_times": start_samples / sfreq,
        "epoch_end_times": end_samples / sfreq,
        "n_epochs": n_epochs,
    }


def create_labels_from_intervals(seg: Dict[str, object], seizure_intervals: List[Tuple[float, float]]) -> np.ndarray:
    y = np.zeros(seg["n_epochs"], dtype=int)
    for i in range(seg["n_epochs"]):
        t0 = seg["epoch_start_times"][i]
        t1 = seg["epoch_end_times"][i]
        for s, e in seizure_intervals:
            if (t0 < e) and (t1 > s):
                y[i] = 1
                break
    return y


def extract_spatial_features_all_epochs(epochs: np.ndarray, fs: float, bands: Dict[str, Tuple[float, float]]) -> np.ndarray:
    """Extract per-epoch channel-wise spectral + statistical features."""
    n_epochs, n_channels, n_samples = epochs.shape
    eps = 1e-12
    freqs, psd = welch(epochs, fs=fs, nperseg=n_samples, axis=-1)
    feat_list = []

    for f_low, f_high in bands.values():
        idx = (freqs >= f_low) & (freqs < f_high)
        if np.any(idx):
            band_energy = simpson(psd[..., idx], freqs[idx], axis=-1)
        else:
            band_energy = np.zeros((n_epochs, n_channels))
        feat_list.append(band_energy)

    feat_list.append(np.sqrt(np.mean(epochs**2, axis=-1)))
    feat_list.append(np.sum(np.abs(np.diff(epochs, axis=-1)), axis=-1))

    std_x = np.std(epochs, axis=-1)
    dx = np.diff(epochs, axis=-1)
    std_dx = np.std(dx, axis=-1)
    ddx = np.diff(dx, axis=-1)
    std_ddx = np.std(ddx, axis=-1)
    feat_list.append((std_ddx / (std_dx + eps)) / ((std_dx / (std_x + eps)) + eps))

    feat_3d = np.stack(feat_list, axis=-1)
    return feat_3d.reshape(n_epochs, n_channels * feat_3d.shape[-1])


def temporal_stack_within_file(X_spatial: np.ndarray, y_epoch: np.ndarray, stack_window: int) -> Tuple[np.ndarray, np.ndarray]:
    """Build temporal context by stacking current + previous epochs."""
    n_epochs, n_feats = X_spatial.shape
    if n_epochs < stack_window:
        return np.empty((0, stack_window * n_feats)), np.empty((0,), dtype=int)

    X_final = np.vstack(
        [X_spatial[i - (stack_window - 1) : i + 1].reshape(-1) for i in range(stack_window - 1, n_epochs)]
    )
    y_final = np.array([y_epoch[i] for i in range(stack_window - 1, n_epochs)], dtype=int)
    return X_final, y_final


# ==========================================================
# Section 4: Feature cache layer (to avoid repeated extraction)
# ==========================================================


def _cache_key(patient_dir: str, summary_path: str, channels: Sequence[str], epoch_len_s: float, stack_window: int, bandpass: Tuple[float, float], bands: Dict[str, Tuple[float, float]]) -> str:
    payload = {
        "patient_dir": os.path.abspath(patient_dir),
        "summary_path": os.path.abspath(summary_path),
        "channels": list(channels),
        "epoch_len_s": epoch_len_s,
        "stack_window": stack_window,
        "bandpass": bandpass,
        "bands": bands,
    }
    return hashlib.md5(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _build_patient_features(patient_dir: str, summary_path: str, channels: Sequence[str], epoch_len_s: float, stack_window: int, bands: Dict[str, Tuple[float, float]], main_bandpass: Tuple[float, float]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[EpochMetadata]]:
    seizure_dict = parse_summary_to_dict(summary_path)
    X_list: List[np.ndarray] = []
    y_list: List[np.ndarray] = []
    group_list: List[str] = []
    meta_list: List[EpochMetadata] = []

    for path in list_edf_files(patient_dir):
        file_name = os.path.basename(path)
        seizure_intervals = seizure_dict.get(file_name, [])

        raw = mne.io.read_raw_edf(path, preload=True, verbose=False)
        normalize_channel_names(raw)
        if not all(ch in raw.ch_names for ch in channels):
            raw.close()
            continue

        raw.pick(list(channels))
        data = raw.get_data()
        fs = raw.info["sfreq"]

        data_bp = bandpass_filter_multich(data, fs, main_bandpass[0], main_bandpass[1])
        seg = segment_eeg_into_epochs(data_bp, fs, epoch_len_s)
        y_epoch = create_labels_from_intervals(seg, seizure_intervals)
        X_spatial = extract_spatial_features_all_epochs(seg["epochs"], fs, bands)
        X_final, y_final = temporal_stack_within_file(X_spatial, y_epoch, stack_window=stack_window)

        if len(y_final) == 0:
            raw.close()
            continue

        X_list.append(X_final)
        y_list.append(y_final)
        group_list.extend([file_name] * len(y_final))

        offset = stack_window - 1
        for idx in range(offset, seg["n_epochs"]):
            meta_list.append(
                EpochMetadata(
                    file_name=file_name,
                    start_s=float(seg["epoch_start_times"][idx]),
                    end_s=float(seg["epoch_end_times"][idx]),
                )
            )
        raw.close()

    if not X_list:
        raise ValueError(f"No usable data for patient directory: {patient_dir}")

    return np.vstack(X_list), np.concatenate(y_list), np.array(group_list), meta_list


def load_or_create_patient_cache(patient_dir: str, summary_path: str, channels: Sequence[str], cache_dir: str, epoch_len_s: float, stack_window: int, bands: Dict[str, Tuple[float, float]], main_bandpass: Tuple[float, float]) -> Dict[str, object]:
    """Load cached patient features when possible; otherwise compute and save."""
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    key = _cache_key(patient_dir, summary_path, channels, epoch_len_s, stack_window, main_bandpass, bands)
    cache_path = os.path.join(cache_dir, f"{Path(patient_dir).name}_{key}.npz")

    if os.path.exists(cache_path):
        data = np.load(cache_path, allow_pickle=True)
        meta = [EpochMetadata(**m) for m in data["meta"]]
        return {
            "X": data["X"],
            "y": data["y"],
            "groups": data["groups"],
            "meta": meta,
            "cache_path": cache_path,
            "cache_hit": True,
        }

    X, y, groups, meta = _build_patient_features(
        patient_dir=patient_dir,
        summary_path=summary_path,
        channels=channels,
        epoch_len_s=epoch_len_s,
        stack_window=stack_window,
        bands=bands,
        main_bandpass=main_bandpass,
    )

    np.savez_compressed(
        cache_path,
        X=X,
        y=y,
        groups=groups,
        meta=np.array([asdict(m) for m in meta], dtype=object),
    )

    return {
        "X": X,
        "y": y,
        "groups": groups,
        "meta": meta,
        "cache_path": cache_path,
        "cache_hit": False,
    }


# ==========================================================
# Section 5: Model blocks (feature selection + 3-model voting)
# ==========================================================


def select_threshold(y_true: np.ndarray, y_score: np.ndarray, thresholds: np.ndarray) -> float:
    best_threshold = thresholds[0]
    best_balanced = -1.0
    for th in thresholds:
        y_pred = (y_score >= th).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        tpr = tp / (tp + fn + 1e-12)
        tnr = tn / (tn + fp + 1e-12)
        balanced = 0.5 * (tpr + tnr)
        if balanced > best_balanced:
            best_balanced = balanced
            best_threshold = th
    return float(best_threshold)


def build_models(k_features: int, random_state: int = 42) -> Dict[str, Pipeline]:
    """Three complementary models sharing same preprocessing/feature-selection stage."""
    return {
        "svm": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("selector", SelectKBest(score_func=f_classif, k=k_features)),
                ("clf", SVC(kernel="rbf", class_weight="balanced", probability=True, random_state=random_state)),
            ]
        ),
        "rf": Pipeline(
            [
                ("selector", SelectKBest(score_func=f_classif, k=k_features)),
                ("clf", RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=random_state, n_jobs=-1)),
            ]
        ),
        "lr": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("selector", SelectKBest(score_func=f_classif, k=k_features)),
                ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=random_state)),
            ]
        ),
    }


def fit_and_vote(models: Dict[str, Pipeline], X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray) -> Tuple[Dict[str, np.ndarray], np.ndarray]:
    scores = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        scores[name] = model.predict_proba(X_test)[:, 1]
    ensemble_score = np.mean(np.column_stack(list(scores.values())), axis=1)
    return scores, ensemble_score


# ==========================================================
# Section 6: Clinical visualization helpers
# ==========================================================


def epochs_to_intervals(times: Sequence[EpochMetadata], y_pred: np.ndarray) -> Dict[str, List[Tuple[float, float]]]:
    intervals: Dict[str, List[Tuple[float, float]]] = {}
    current_file = None
    current_start = None

    for meta, pred in zip(times, y_pred, strict=False):
        if current_file is None:
            current_file = meta.file_name

        if meta.file_name != current_file:
            if current_start is not None:
                intervals.setdefault(current_file, []).append((current_start, prev_end))
            current_file = meta.file_name
            current_start = None

        if pred == 1 and current_start is None:
            current_start = meta.start_s
        if pred == 0 and current_start is not None:
            intervals.setdefault(meta.file_name, []).append((current_start, prev_end))
            current_start = None

        prev_end = meta.end_s

    if current_start is not None and current_file is not None:
        intervals.setdefault(current_file, []).append((current_start, prev_end))

    return intervals


def plot_score_timeline(file_name: str, times: Sequence[EpochMetadata], scores: np.ndarray, threshold: float, output_dir: str) -> None:
    mask = np.array([meta.file_name == file_name for meta in times])
    if not np.any(mask):
        return

    file_times = [meta.start_s for meta, flag in zip(times, mask, strict=False) if flag]
    file_scores = scores[mask]

    plt.figure(figsize=(12, 3))
    plt.plot(file_times, file_scores, label="Seizure probability")
    plt.axhline(threshold, color="red", linestyle="--", label=f"Threshold={threshold:.2f}")
    plt.xlabel("Time (s)")
    plt.ylabel("Probability")
    plt.title(f"Clinical timeline - {file_name}")
    plt.grid(True)
    plt.legend()
    out_path = os.path.join(output_dir, f"{file_name}_score_timeline.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def plot_multichannel_waveform(raw: mne.io.BaseRaw, channels: Sequence[str], start_s: float, end_s: float, output_path: str) -> None:
    raw_crop = raw.copy().pick(list(channels)).crop(tmin=start_s, tmax=end_s)
    data = raw_crop.get_data()
    times = raw_crop.times
    n_channels = data.shape[0]

    offsets = np.arange(n_channels) * np.nanmax(np.abs(data)) * 2.5
    plt.figure(figsize=(12, 6))
    for idx, ch in enumerate(channels):
        plt.plot(times, data[idx] + offsets[idx], linewidth=0.7, label=ch)
    plt.yticks([])
    plt.xlabel("Time (s)")
    plt.title(f"Raw EEG waveforms ({start_s:.1f}-{end_s:.1f}s)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


# ==========================================================
# Section 7: Unified pipeline entry (3-patient LOOCV by default)
# ==========================================================


def run_unified_pipeline(patient_dirs: Sequence[str], summary_paths: Sequence[str], output_dir: str, cache_dir: str, epoch_len_s: float, stack_window: int, bands: Dict[str, Tuple[float, float]], main_bandpass: Tuple[float, float], max_patients: int, k_features: int) -> None:
    if len(patient_dirs) != len(summary_paths):
        raise ValueError("Number of patient directories must match number of summary paths.")

    selected_pairs = list(zip(patient_dirs, summary_paths, strict=True))[:max_patients]
    patient_dirs = [p for p, _ in selected_pairs]
    summary_paths = [s for _, s in selected_pairs]

    os.makedirs(output_dir, exist_ok=True)
    channels = find_common_channels(patient_dirs)

    patient_data = {}
    for patient_dir, summary_path in zip(patient_dirs, summary_paths, strict=True):
        cached = load_or_create_patient_cache(
            patient_dir=patient_dir,
            summary_path=summary_path,
            channels=channels,
            cache_dir=cache_dir,
            epoch_len_s=epoch_len_s,
            stack_window=stack_window,
            bands=bands,
            main_bandpass=main_bandpass,
        )
        patient_data[patient_dir] = cached
        print(f"[CACHE] {Path(patient_dir).name}: {'HIT' if cached['cache_hit'] else 'MISS'} -> {cached['cache_path']}")

    for test_patient in patient_dirs:
        train_patients = [p for p in patient_dirs if p != test_patient]
        X_train = np.vstack([patient_data[p]["X"] for p in train_patients])
        y_train = np.concatenate([patient_data[p]["y"] for p in train_patients])
        groups_train = np.concatenate([patient_data[p]["groups"] for p in train_patients])

        X_test = patient_data[test_patient]["X"]
        y_test = patient_data[test_patient]["y"]
        meta_test = patient_data[test_patient]["meta"]

        gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        train_idx, val_idx = next(gss.split(X_train, y_train, groups_train))

        models = build_models(k_features=min(k_features, X_train.shape[1]))

        _, val_ensemble = fit_and_vote(models, X_train[train_idx], y_train[train_idx], X_train[val_idx])
        threshold = select_threshold(y_train[val_idx], val_ensemble, np.linspace(0.05, 0.95, 19))

        model_scores, test_ensemble = fit_and_vote(models, X_train, y_train, X_test)
        y_pred = (test_ensemble >= threshold).astype(int)

        patient_name = os.path.basename(test_patient.rstrip("/"))
        patient_out_dir = os.path.join(output_dir, patient_name)
        os.makedirs(patient_out_dir, exist_ok=True)

        report_payload = {
            "patient": patient_name,
            "channels": channels,
            "threshold": threshold,
            "average_precision": average_precision_score(y_test, test_ensemble),
            "roc_auc": roc_auc_score(y_test, test_ensemble) if len(np.unique(y_test)) > 1 else float("nan"),
            "classification_report": classification_report(y_test, y_pred, output_dict=True, zero_division=0),
            "per_model_ap": {name: average_precision_score(y_test, s) for name, s in model_scores.items()},
            "predicted_intervals": epochs_to_intervals(meta_test, y_pred),
        }

        with open(os.path.join(patient_out_dir, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(report_payload, f, indent=2, ensure_ascii=False)

        for file_name in sorted(set(meta.file_name for meta in meta_test)):
            plot_score_timeline(file_name=file_name, times=meta_test, scores=test_ensemble, threshold=threshold, output_dir=patient_out_dir)

        for file_name, interval_list in report_payload["predicted_intervals"].items():
            edf_path = os.path.join(test_patient, file_name)
            if not os.path.exists(edf_path):
                continue
            raw = mne.io.read_raw_edf(edf_path, preload=True, verbose=False)
            normalize_channel_names(raw)
            for idx, (start_s, end_s) in enumerate(interval_list):
                output_path = os.path.join(patient_out_dir, f"{file_name}_interval_{idx + 1}_{start_s:.0f}-{end_s:.0f}.png")
                plot_multichannel_waveform(raw=raw, channels=channels, start_s=start_s, end_s=end_s, output_path=output_path)
            raw.close()


# ==========================================================
# Section 8: CLI
# ==========================================================


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unified EEG pipeline with 3-model voting, feature selection, LOOCV and caching.")
    parser.add_argument("--patient-dirs", nargs="+", required=True, help="Patient EDF folders.")
    parser.add_argument("--summary-paths", nargs="+", required=True, help="Patient summary txt files.")
    parser.add_argument("--output-dir", default="loo_outputs", help="Output directory for reports and plots.")
    parser.add_argument("--cache-dir", default="feature_cache", help="Persistent feature cache directory.")
    parser.add_argument("--max-patients", type=int, default=3, help="How many patients to use (default=3 for fast LOOCV).")
    parser.add_argument("--epoch-len", type=float, default=2.0, help="Epoch length in seconds.")
    parser.add_argument("--stack-window", type=int, default=3, help="Temporal stacking window.")
    parser.add_argument("--k-features", type=int, default=256, help="Number of selected features before model fitting.")
    parser.add_argument("--bandpass-low", type=float, default=0.5, help="Main bandpass low cutoff.")
    parser.add_argument("--bandpass-high", type=float, default=30.0, help="Main bandpass high cutoff.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run_unified_pipeline(
        patient_dirs=args.patient_dirs,
        summary_paths=args.summary_paths,
        output_dir=args.output_dir,
        cache_dir=args.cache_dir,
        epoch_len_s=args.epoch_len,
        stack_window=args.stack_window,
        bands=DEFAULT_BANDS,
        main_bandpass=(args.bandpass_low, args.bandpass_high),
        max_patients=args.max_patients,
        k_features=args.k_features,
    )


if __name__ == "__main__":
    main()
