# Clinical Error Analysis (v1-v5)

This directory is a formal part of the EE6019 project, not a detached side experiment.
The work extends the canonical patient-specific Random Forest pipeline with event-level
failure analysis and controlled follow-up experiments that were discussed in the final report.

## Why this branch exists

Aggregate seizure-detection metrics do not explain *why* a detector fails. This branch
moves from patient-level summaries to individual events and traces, then uses those failure
modes to design and accept/reject targeted model or post-processing changes.

Two recurring cases drove the analysis:

- `chb04`: delayed true-positive behaviour.
- `chb08`: excessive false-positive burden.

The branch retains the same underlying RF pipeline and evaluation logic rather than
replacing the complete project with a separate model family.
## Iteration history

| Version | Main question | Outcome |
| --- | --- | --- |
| v1 | What are the dominant clinical failure modes? | Identified delayed-TP and FP-heavy cases; early artifact-aware changes did not generalise safely. |
| v2 | Which component of the apparent improvement is actually useful? | Proxy augmentation emerged as the useful component; aggressive suppression hurt sensitivity. |
| v3 | Can the proxy set be reduced without losing the benefit? | Smaller variants exposed focus-vs-global trade-offs; the hybrid family came close but missed the global guard. |
| v4 | Can one minimal add-back recover the chb04 miss? | Sensitivity recovered, but delay worsened. |
| v5 | Can timing policy fix the delay without increasing false alarms? | Earlier triggering reduced delay but caused unacceptable FAR growth; the global threshold-lowering direction was rejected. |

## Global guard

A candidate was not accepted merely because it improved the focus patients. Later iterations
required it to avoid new zero-sensitivity patients, limit macro-sensitivity loss, reduce macro
FAR, improve chb08 FAR, and avoid worsening chb04 delay.

The strongest accepted improvement across the branch was the proxy-augmented RF variant,
which preserved macro sensitivity while reducing false-alarm burden. Later v4/v5 experiments
were valuable negative results: they narrowed the remaining problem to selective onset timing
rather than a need for globally lower thresholds.
