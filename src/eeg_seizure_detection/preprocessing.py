"""EEG channel normalization, alignment, labelling and filtering."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import mne
import numpy as np
from scipy.signal import butter, medfilt, sosfiltfilt

from .config import ExperimentConfig

def normalize_channel_name(name: str) -> str:
    name = name.strip().upper()
    name = re.sub('-\\d+$', '', name)
    name = re.sub('\\s+', '', name)
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

def align_channels(raw: mne.io.BaseRaw, target_channels: Sequence[str], policy: str='strict') -> Tuple[np.ndarray, Dict[str, Any]]:
    normalized_targets = [normalize_channel_name(ch) for ch in target_channels]
    raw_data = raw.get_data()
    existing_names = [normalize_channel_name(ch) for ch in raw.ch_names]
    name_to_idx = {name: idx for idx, name in enumerate(existing_names)}
    n_ch = len(normalized_targets)
    missing_channels = []
    reversed_channels = []
    n_times = raw_data.shape[1]
    data = np.zeros((n_ch, n_times), dtype=raw_data.dtype)
    for i, target in enumerate(normalized_targets):
        idx = name_to_idx.get(target)
        if idx is not None:
            data[i] = raw_data[idx]
            continue
        if '-' in target:
            reverse_target = '-'.join(target.split('-')[::-1])
            reverse_idx = name_to_idx.get(reverse_target)
            if reverse_idx is not None:
                np.negative(raw_data[reverse_idx], out=data[i])
                reversed_channels.append(target)
                continue
        if policy == 'zero_fill':
            missing_channels.append(target)
        else:
            raise ValueError(f'Missing target channel: {target}')
    info = {'missing_channels': missing_channels, 'missing_count': len(missing_channels), 'reversed_channels': reversed_channels}
    return (data, info)

def build_epoch_labels(n_epochs: int, epoch_len_s: int, seizure_intervals: Sequence[Tuple[int, int]]) -> np.ndarray:
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

_SOS_CACHE: Dict[Tuple[int, float, float, int], np.ndarray] = {}

def bandpass_filter_multich(data: np.ndarray, fs: int, lowcut: float, highcut: float, method: str='butter_sos', butter_order: int=4) -> np.ndarray:
    method = str(method).lower()
    if method == 'butter_sos':
        key = (int(fs), float(lowcut), float(highcut), int(butter_order))
        sos = _SOS_CACHE.get(key)
        if sos is None:
            nyquist = 0.5 * fs
            if highcut >= nyquist:
                raise ValueError(f'highcut={highcut} must be < Nyquist {nyquist}.')
            sos = butter(int(butter_order), [lowcut / nyquist, highcut / nyquist], btype='bandpass', output='sos')
            _SOS_CACHE[key] = sos
        return sosfiltfilt(sos, data, axis=1)
    if method == 'fir_zero':
        return mne.filter.filter_data(data=data, sfreq=float(fs), l_freq=float(lowcut), h_freq=float(highcut), method='fir', phase='zero', verbose=False)
    raise ValueError(f'Unsupported bandpass method: {method}')

def align_channels_window(raw: mne.io.BaseRaw, target_channels: Sequence[str], start_idx: int, stop_idx: int, policy: str='strict') -> Tuple[np.ndarray, Dict[str, Any]]:
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
        if '-' in target:
            reverse_target = '-'.join(target.split('-')[::-1])
            if reverse_target in existing:
                data[i] = -raw.get_data(picks=[existing[reverse_target]], start=start_idx, stop=stop_idx)[0]
                reversed_channels.append(target)
                continue
        if policy == 'zero_fill':
            missing_channels.append(target)
        else:
            raise ValueError(f'Missing target channel: {target}')
    info = {'missing_channels': missing_channels, 'missing_count': len(missing_channels), 'reversed_channels': reversed_channels}
    return (data, info)

def load_filtered_eeg_segment(cfg: ExperimentConfig, patient_id: str, file_name: str, start_time_s: float, end_time_s: float, onset_time_s: float, plot_channels: Sequence[str]) -> Tuple[np.ndarray, np.ndarray, List[str], Dict[str, Any]]:
    edf_path = Path(cfg.data_root) / patient_id / file_name
    if not edf_path.exists():
        raise FileNotFoundError(f'EDF not found: {edf_path}')
    raw = mne.io.read_raw_edf(edf_path, preload=False, verbose=False)
    raw = deduplicate_and_normalize_raw(raw)
    fs = int(raw.info['sfreq'])
    start_idx = max(0, int(start_time_s * fs))
    stop_idx = min(raw.n_times, int(end_time_s * fs))
    if stop_idx <= start_idx:
        raw.close()
        raise ValueError('Invalid EEG window: stop <= start')
    data_window, align_info = align_channels_window(raw=raw, target_channels=cfg.channels, start_idx=start_idx, stop_idx=stop_idx, policy=cfg.feature.channel_missing_policy)
    raw.close()
    if cfg.feature.scale_to_uV:
        data_window = data_window * 1000000.0
    data_bp = bandpass_filter_multich(data_window, fs=fs, lowcut=cfg.feature.bandpass_low_hz, highcut=cfg.feature.bandpass_high_hz, method=cfg.feature.bandpass_method, butter_order=cfg.feature.butter_order)
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
    t_abs = np.arange(eeg_plot.shape[1]) / fs + start_idx / fs
    t_rel = t_abs - onset_time_s
    return (eeg_plot, t_rel, plot_names, align_info)
