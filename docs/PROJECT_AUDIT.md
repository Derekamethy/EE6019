# EEG Seizure Detection GitHub Publication Audit

## Evidence precedence
1. The preserved original `Final code/EE6019 Final Code.ipynb` is the primary historical executable evidence outside this public release working copy.
2. `EE6019_Final_Report.pdf` is the primary reported-result and methodological narrative in the preserved original project directory.
3. Selected exported figures provide visual evidence for reported comparisons.
4. Clinical Error Analysis v1-v5 notebooks and reports are first-class reported evidence corresponding to Chapter 6.4 / Table 8 of the final report.

## Public implementation structure
The recruiter-facing implementation is now maintained as responsibility-specific Python modules under `src/eeg_seizure_detection/`. `legacy_core.py` is compatibility-only and re-exports the modular implementation rather than containing a second copy of the algorithm.

The notebooks under `notebooks/reference/` are English, output-free historical references. They are not the primary engineering code interface. The separate 1D-CNN experiment is implemented under `extensions/cnn/` and remains distinct from the headline Random Forest benchmark.

Clinical Error Analysis v1-v5 remains preserved under `clinical_error_analysis/reference_notebooks/`, together with written reports and exported evidence. These notebooks document the reported iteration lineage but are not presented as the main software architecture.

## Canonical public claim
The final reported system is a patient-specific Random Forest seizure detector using CHB-MIT EEG, engineered spectral/synchrony features, fold-local top-k feature selection, validation-selected alarm thresholds, and event-level evaluation.

## Excluded exploratory work
`EE6019_DL_DG_Rebuild` is a later exploratory software/domain-generalisation redesign. It is intentionally excluded because real-data validation was not completed.

## Public report copy
`EE6019_Final_Report_PUBLIC_REDACTED.pdf` is a privacy-redacted public copy. The original report remains untouched outside `github_release`; only the cover page was replaced to remove the student identification number, while pages 2-49 were preserved unchanged.

## Claims to avoid
- No unseen-patient generalisation claim for the canonical Random Forest.
- No clinical validation or medical-device claim.
- No target-hardware latency or power claim.
- Do not present the 20.67 KB single-subject C representation proof as the final cohort-validated model.
- Do not imply that feature reduction automatically reduced end-to-end feature-computation cost without a measured benchmark.
