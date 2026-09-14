# EEG Seizure Detection from Multichannel Scalp EEG

An engineering machine-learning project for retrospective seizure-event detection on the
CHB-MIT scalp EEG dataset. The repository combines the canonical EE6019 implementation with
the later clinical-error-analysis iterations that were part of the reported project work.

## Project focus

The objective was not only to classify short EEG windows, but to build an inspectable
signal-to-event pipeline that controls false alarms, preserves validation boundaries, and
makes deployment trade-offs visible.

The canonical pipeline covers:

1. EDF loading and annotation parsing.
2. Bipolar-channel alignment, including reversed-polarity handling.
3. 0.5-50 Hz zero-phase Butterworth filtering.
4. Non-overlapping 2 s epoch generation and seizure-overlap labelling.
5. Spectral and synchrony feature extraction.
6. Temporal stacking across the current and three preceding epochs.
7. Fold-local feature selection and patient-specific model training.
8. Validation-selected thresholding, smoothing and minimum-duration event logic.
9. Event-level sensitivity, false-alarm rate and detection-delay evaluation.
10. Model-size, latency and C-export feasibility analysis.
## Canonical study scope

The final reported study used subjects `chb01`-`chb10`, covering 580.57 hours and 55
annotated seizure events. Evaluation was patient-specific and within-subject, using
file-level leave-one-seizure-out logic; it was **not** unseen-patient generalisation.

Headline reported results:

| Metric | Reported value |
| --- | ---: |
| Macro event sensitivity | 0.98 |
| Median subject FAR | 0.2455 events/hour |
| Mean delay for detected events | 10.64 s |
| Pooled seizure capture | 53 / 55 |

The main final classifier used a 500-tree Random Forest with 30 selected inputs. SVM and
XGBoost baselines, full-vs-reduced feature comparisons, latency profiling, model-size
analysis and C-export feasibility are retained in the canonical notebook/report.

## Clinical error analysis: v1-v5

The project also includes a five-stage clinical error-analysis branch. It drills down from
aggregate metrics to event-level traces, especially delayed detection in `chb04` and
false-positive burden in `chb08`, then evaluates targeted proxy-feature and timing changes.

This work is included under [`clinical_error_analysis/`](clinical_error_analysis/) as a
first-class part of the project, with all five notebooks, corresponding reports, and the
v5 exported evidence tables/figures.
## Repository layout

```text
notebooks/canonical/          Original final research notebooks (copied, never edited in place)
src/eeg_seizure_detection/   Reusable code extracted from the canonical notebook
clinical_error_analysis/     v1-v5 notebooks, reports and exported evidence
assets/                      Key result figures
data/                        Dataset access and redistribution notes
docs/                        Final report and repository audit
scripts/                     Reproducibility and code-extraction utilities
```

## Data and reproducibility

Raw CHB-MIT EDF recordings are not redistributed here. Obtain the dataset through its
authorised public source, then configure the local data path before running the research
pipeline. The notebook contains the original experiment orchestration; `legacy_core.py`
is an automatically extracted readable library view of its functions/classes, not a claim
that the historical experiment has been re-run from scratch in this cleaned repository.

## Scope and limitations

- Academic retrospective research prototype; not a medical device.
- No claim of clinical validation or patient benefit.
- Headline results are patient-specific, not cross-patient generalisation.
- Zero-phase filtering and centred smoothing are offline/non-causal operations.
- Reported latency was measured in the Python environment, not on target embedded hardware.
- The separate exploratory deep-learning/domain-generalisation rebuild is intentionally
  excluded from this repository because it was not part of the validated project results.

## Author

Yangdeyi Yang — MSc Electronic & Electrical Engineering, University College Cork.
