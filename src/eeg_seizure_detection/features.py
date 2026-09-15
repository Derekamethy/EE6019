"""Feature extraction, temporal stacking and fold-local selection."""
from .legacy_core import (
    build_base_feature_names,
    build_stacked_feature_names,
    extract_base_features_for_file,
    get_band_tuples,
    get_synchrony_index_pairs,
    select_top_k_features_tree,
    temporal_stack_features,
    topk_feature_cache_hash,
)

__all__ = [
    "get_band_tuples",
    "get_synchrony_index_pairs",
    "extract_base_features_for_file",
    "temporal_stack_features",
    "build_base_feature_names",
    "build_stacked_feature_names",
    "select_top_k_features_tree",
    "topk_feature_cache_hash",
]
