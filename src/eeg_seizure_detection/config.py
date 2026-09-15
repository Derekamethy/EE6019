"""Configuration interface for the canonical EE6019 pipeline."""
from copy import deepcopy
from pathlib import Path
from typing import Sequence

from .legacy_core import (
    CFG,
    EvalConfig,
    ExperimentConfig,
    ExportConfig,
    FeatureConfig,
)


def make_final_rf_config(
    data_root: str | Path,
    patient_ids: Sequence[str] | None = None,
) -> ExperimentConfig:
    """Return the reported final RF configuration with a caller-owned data path."""
    cfg = deepcopy(CFG)
    cfg.data_root = str(data_root)
    cfg.feature.history_epochs = 3
    cfg.feature.bandpass_method = "butter_sos"
    cfg.feature.butter_order = 4
    cfg.eval.top_k_features = 30
    cfg.eval.rf_n_estimators = 500
    cfg.eval.rf_max_depth = 12
    cfg.eval.rf_min_samples_leaf = 1
    cfg.eval.rf_max_features = "sqrt"
    cfg.eval.fixed_threshold_mode = False
    if patient_ids is not None:
        cfg.eval.patient_ids = tuple(patient_ids)
    return cfg


__all__ = [
    "FeatureConfig",
    "EvalConfig",
    "ExportConfig",
    "ExperimentConfig",
    "make_final_rf_config",
]
