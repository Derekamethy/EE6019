"""Validation, threshold selection and event-level evaluation."""
from .legacy_core import (
    build_event_detection_matrix,
    choose_threshold_from_validation,
    compute_event_metrics,
    count_events,
    evaluate_many_patients,
    evaluate_patient_loso,
    extract_binary_runs,
    split_inner_validation_files,
)

__all__ = [
    "choose_threshold_from_validation",
    "split_inner_validation_files",
    "count_events",
    "extract_binary_runs",
    "compute_event_metrics",
    "evaluate_patient_loso",
    "evaluate_many_patients",
    "build_event_detection_matrix",
]
