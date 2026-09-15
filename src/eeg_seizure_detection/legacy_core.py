"""Compatibility imports for code that used the earlier monolithic core module."""

from .config import (FeatureConfig, EvalConfig, ExportConfig, ExperimentConfig, GLOBAL_SEED, CFG, CACHE_SCHEMA_VERSION)
from .io_utils import (ensure_dir, make_json_safe, _CONFIG_HASH_CACHE, config_to_hash, save_json, load_json, get_patient_cache_path, get_export_paths)
from .preprocessing import (normalize_channel_name, deduplicate_and_normalize_raw, align_channels, build_epoch_labels, _SOS_CACHE, bandpass_filter_multich, align_channels_window, load_filtered_eeg_segment)
from .features import (get_band_tuples, get_synchrony_index_pairs, _BAND_MASK_CACHE, _SYNC_INDEX_CACHE, _get_band_masks, extract_base_features_for_file, temporal_stack_features, _BASE_FEATURE_NAMES_CACHE, build_base_feature_names, _STACKED_FEATURE_NAMES_CACHE, build_stacked_feature_names)
from .data import (parse_summary_to_dict, build_patient_cache, build_all_caches, load_patient_cache, load_all_caches, summarize_caches, build_patient_matrix_index, collect_rows_from_matrix_index, collect_rows_from_files)
from .models import (sample_training_rows, make_model, compute_scale_pos_weight, topk_feature_cache_hash, select_top_k_features_tree, train_patient_bundle)
from .evaluation import (apply_duration_constraint, count_events, extract_binary_runs, compute_event_metrics, choose_threshold_from_validation, split_inner_validation_files, evaluate_patient_loso, evaluate_many_patients, build_event_detection_matrix)
from .experiments import (_safe_float, _aggregate_summary, _priority_sort, _run_rf_eval, _build_macro_row, _sort_benchmark, resolve_final_rf_context, annotate_bars, _md, _safe_copy_df, _show_df, _reorder_cols, _add_metric_rank)
from .deployment import (benchmark_single_epoch_latency, profile_rf_model)
from .clinical import (build_clinical_case_dataframe)

# New code should import from the responsibility-specific modules above.
