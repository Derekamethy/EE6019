"""Deployment-feasibility helpers from the canonical notebook."""
from .legacy_core import (
    benchmark_single_epoch_latency,
    get_export_paths,
    profile_rf_model,
)

__all__ = [
    "benchmark_single_epoch_latency",
    "profile_rf_model",
    "get_export_paths",
]
