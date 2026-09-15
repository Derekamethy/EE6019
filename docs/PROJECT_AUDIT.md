# Evidence and Claim Guide

## Evidence precedence

1. [`EE6019_Final_Report_PUBLIC_REDACTED.pdf`](EE6019_Final_Report_PUBLIC_REDACTED.pdf) is the primary public narrative for the reported methodology and results.
2. [`notebooks/reference/`](../notebooks/reference/) contains notebook-form references for the final RF workflow and the separate 1D-CNN comparison.
3. [`src/eeg_seizure_detection/`](../src/eeg_seizure_detection/) is the maintained engineering implementation of the reported classical-ML pipeline.
4. [`clinical_error_analysis/`](../clinical_error_analysis/) contains the reported v1-v5 failure-analysis lineage, written reports, and exported evidence corresponding to Chapter 6.4 / Table 8 of the final report.

## Primary public claim

The headline system is a patient-specific Random Forest seizure detector for CHB-MIT EEG using engineered spectral/synchrony features, temporal context, fold-local Top-30 feature selection, validation-selected alarm thresholds, and event-level evaluation.

## Implementation boundaries

The modular Python package is the primary code interface. Reference notebooks are included to make the experimental sequence inspectable, but they are not the maintained software architecture. The 1D-CNN implementation under [`extensions/cnn/`](../extensions/cnn/) is an experimental comparison rather than the headline benchmark.

Clinical Error Analysis v1-v5 is part of the reported project evidence. Its branch-level metrics use a reconciled evaluation snapshot and should not be mixed directly with the main headline benchmark.

## Excluded exploratory work

A later deep-learning/domain-generalisation redesign is not included because it did not contribute validated real-data results to the reported project.

## Claim boundaries

- No unseen-patient generalisation claim for the headline Random Forest system.
- No clinical validation or medical-device claim.
- No target-hardware latency or power claim.
- The 20.67 KB single-subject C representation proof is not the final cohort-validated model.
- Feature reduction should not be interpreted as measured end-to-end feature-computation savings without a dedicated benchmark.
