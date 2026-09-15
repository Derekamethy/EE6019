# EE6019 GitHub Publication Audit

## Canonical evidence

1. `Final code/EE6019 Final Code.ipynb` - primary executable implementation.
2. `EE6019_Final_Report.pdf` - primary reported-result and methodological narrative in the preserved original project directory.
3. Selected exported figures from the final code directory.
4. Clinical Error Analysis v1-v5 notebooks and reports - reported project evidence corresponding to Chapter 6.4 / Table 8 of the final report.

## Canonical public claim

The final reported system is a patient-specific Random Forest seizure detector using CHB-MIT EEG, engineered spectral/synchrony features, fold-local top-k feature selection, validation-selected alarm thresholds, and event-level evaluation.

## Reported analysis and separate experiments

- Clinical Error Analysis v1-v5 is first-class reported project work. It was developed in separate notebooks rather than merged into the large final notebook, but it is explicitly documented in the final report and is retained in this repository.
- `EE6019 Final Code - 1DCNN Addon.ipynb` is a separate 1D-CNN experiment over engineered feature sequences; it is not the canonical headline benchmark.
- `EE6019_DL_DG_Rebuild` is a later exploratory software/domain-generalisation redesign. It is intentionally excluded from the public EE6019 repository because real-data validation was not completed.

## Public report copy

`EE6019_Final_Report_PUBLIC_REDACTED.pdf` is a privacy-redacted public copy. The original report remains untouched outside `github_release`; only the cover page was replaced to remove the student identification number, while pages 2-49 were preserved unchanged.
## Claims to avoid

- No unseen-patient generalisation claim for the canonical Random Forest.
- No clinical validation or medical-device claim.
- No target-hardware latency or power claim.
- Do not present the 20.67 KB single-subject C representation proof as the final cohort-validated model.
- Do not imply that feature reduction automatically reduced end-to-end feature-computation cost without a measured benchmark.
