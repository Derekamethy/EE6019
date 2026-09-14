"""Signal filtering and temporal post-processing helpers."""
from .legacy_core import (
    apply_duration_constraint,
    bandpass_filter_multich,
)

__all__ = [
    "bandpass_filter_multich",
    "apply_duration_constraint",
]
