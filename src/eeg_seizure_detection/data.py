"""Data ingestion, channel alignment and cache management."""
from .legacy_core import (
    align_channels,
    align_channels_window,
    build_all_caches,
    build_epoch_labels,
    build_patient_cache,
    deduplicate_and_normalize_raw,
    load_all_caches,
    load_filtered_eeg_segment,
    load_patient_cache,
    normalize_channel_name,
    parse_summary_to_dict,
    summarize_caches,
)

__all__ = [
    "parse_summary_to_dict",
    "normalize_channel_name",
    "deduplicate_and_normalize_raw",
    "align_channels",
    "align_channels_window",
    "build_epoch_labels",
    "build_patient_cache",
    "build_all_caches",
    "load_patient_cache",
    "load_all_caches",
    "summarize_caches",
    "load_filtered_eeg_segment",
]
