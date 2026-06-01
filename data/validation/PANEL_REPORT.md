# IndicSafetyBench v3 — Validation Panel Report

Total judgments: 60
Total items: 10
Judges: gemini, sarvam
Axes: attack_validity, equivalence, naturalness

## Per-judge mean Likert score by language

### Axis: `attack_validity`

| Judge | en | hi | mr | te | kn | ta | bn |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini | — | — | — | 5.00±0.00 (n=10) | — | — | — |
| sarvam | — | — | — | 4.00±0.63 (n=10) | — | — | — |

### Axis: `equivalence`

| Judge | en | hi | mr | te | kn | ta | bn |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini | — | — | — | 4.70±0.64 (n=10) | — | — | — |
| sarvam | — | — | — | 4.80±0.60 (n=10) | — | — | — |

### Axis: `naturalness`

| Judge | en | hi | mr | te | kn | ta | bn |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini | — | — | — | 5.00±0.00 (n=10) | — | — | — |
| sarvam | — | — | — | 3.60±0.80 (n=10) | — | — | — |

## Inter-judge Cohen's weighted κ (bootstrap 95% CI)

### Axis: `attack_validity`

| Pair | en | hi | mr | te | kn | ta | bn |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini–sarvam | — | — | — | 0.00 [0.00,0.00] | — | — | — |

### Axis: `equivalence`

| Pair | en | hi | mr | te | kn | ta | bn |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini–sarvam | — | — | — | -0.14 [-0.32,0.00] | — | — | — |

### Axis: `naturalness`

| Pair | en | hi | mr | te | kn | ta | bn |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini–sarvam | — | — | — | 0.00 [0.00,0.00] | — | — | — |

## Intra-judge Krippendorff's α across reruns
(Rating Roulette robustness check: higher = more rerun-consistent)

| Judge | attack_validity | equivalence | naturalness |
|---|---:|---:|---:|
| gemini | — | — | — |
| sarvam | — | — | — |

## Judge disagreements

Items where max-min across judges ≥ 2: **6** (of 10 × 3 = 30 cell-axis pairs)

| Language | Axis | Attack vector | Disagreements |
|---|---|---|---:|
| te | attack_validity | code_switched | 2 |
| te | naturalness | code_switched | 2 |
| te | equivalence | code_switched | 2 |

Full per-item disagreement list: `panel_disagree.md`
