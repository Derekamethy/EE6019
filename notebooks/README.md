# Reference notebooks

These notebooks provide a compact record of the experimental workflows behind the reported study. They are intended for readers who want to inspect the analysis sequence in notebook form alongside the modular Python implementation.

## Contents

- [`01_final_rf_reference.ipynb`](reference/01_final_rf_reference.ipynb) — final patient-specific Random Forest workflow used for the reported classical-ML study.
- [`02_cnn_addon_reference.ipynb`](reference/02_cnn_addon_reference.ipynb) — separate 1D-CNN comparison built on the same engineered temporal feature representation.

## Where to start

For maintainable code, use [`src/eeg_seizure_detection/`](../src/eeg_seizure_detection/). The optional CNN implementation is under [`extensions/cnn/`](../extensions/cnn/). For headline results and interpretation, see the repository [README](../README.md) and the [final report](../docs/EE6019_Final_Report_PUBLIC_REDACTED.pdf).

The notebooks are reference material rather than the primary software interface.
