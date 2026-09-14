# EE6019 GitHub Publication Audit

## Canonical evidence

1. `Final code/EE6019 Final Code.ipynb` — primary executable implementation.
2. `EE6019_Final_Report.pdf` — primary reported-result and methodological narrative.
3. Selected exported figures from the final code directory.

## Canonical public claim

The final reported system is a patient-specific Random Forest seizure detector using CHB-MIT EEG, engineered spectral/synchrony features, fold-local top-k feature selection, validation-selected alarm thresholds, and event-level evaluation.

## Experimental extensions

- `EE6019 Final Code - 1DCNN Addon.ipynb`: later 1D-CNN experiment over engineered feature sequences; not part of the canonical report benchmark.
- Clinical-error-analysis v1–v5: later diagnostic/refinement branch. It should be presented as post-project extension unless its exact provenance is explicitly documented.
- `EE6019_DL_DG_Rebuild`: later software/DG redesign. Real-data validation has not been performed, so synthetic tests are software checks only.

## Claims to avoid

- No unseen-patient generalisation claim for the canonical RF.
- No clinical validation or medical-device claim.
- No target-hardware latency/power claim.
- Do not present the 20.67 KB single-subject C representation proof as the final cohort-validated model.
- Do not imply feature reduction automatically reduced end-to-end feature-computation cost without a measured benchmark.