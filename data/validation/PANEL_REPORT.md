# IndicSafetyBench v3 — Validation Panel Report

Total judgments: 2911
Total items: 600
Judges: gemini, sarvam
Axes: attack_validity, equivalence, naturalness

## Per-judge mean Likert score by language

### Axis: `attack_validity`

| Judge | en | hi | mr | te | kn | ta | bn |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini | 5.00±0.00 (n=30) | 4.92±0.33 (n=60) | 4.87±0.50 (n=60) | 4.88±0.58 (n=60) | 4.78±0.58 (n=60) | 4.88±0.58 (n=60) | 4.75±0.79 (n=60) |
| sarvam | 3.67±0.47 (n=3) | 4.38±0.49 (n=13) | 4.22±0.71 (n=18) | 4.00±0.00 (n=2) | 4.29±0.45 (n=14) | 4.33±0.47 (n=18) | 4.09±1.08 (n=11) |

### Axis: `equivalence`

| Judge | en | hi | mr | te | kn | ta | bn |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini | 4.98±0.13 (n=60) | 4.97±0.23 (n=90) | 4.98±0.15 (n=90) | 4.91±0.38 (n=90) | 4.91±0.53 (n=90) | 4.96±0.25 (n=90) | 4.99±0.10 (n=90) |
| sarvam | 5.00±0.00 (n=57) | 4.92±0.46 (n=89) | 4.99±0.11 (n=88) | 5.00±0.00 (n=84) | 4.99±0.11 (n=83) | 4.98±0.15 (n=85) | 4.96±0.19 (n=84) |

### Axis: `naturalness`

| Judge | en | hi | mr | te | kn | ta | bn |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini | 4.98±0.13 (n=60) | 4.21±1.22 (n=90) | 4.52±0.97 (n=90) | 4.30±1.19 (n=90) | 4.33±1.04 (n=90) | 4.34±1.07 (n=90) | 4.60±0.88 (n=90) |
| sarvam | 4.00±0.82 (n=45) | 3.57±0.81 (n=49) | 3.17±0.80 (n=36) | 3.33±0.75 (n=42) | 2.85±0.84 (n=34) | 3.22±0.99 (n=32) | 3.20±0.84 (n=44) |

## Inter-judge Cohen's weighted κ (bootstrap 95% CI)

### Axis: `attack_validity`

| Pair | en | hi | mr | te | kn | ta | bn |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini–sarvam | — | 0.00 [0.00,0.00] | 0.00 [0.00,0.00] | — | 0.00 [0.00,0.00] | 0.06 [0.00,0.23] | 0.00 [0.00,0.00] |

### Axis: `equivalence`

| Pair | en | hi | mr | te | kn | ta | bn |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini–sarvam | 0.00 [0.00,0.00] | -0.02 [-0.04,0.00] | -0.02 [-0.04,0.00] | 0.00 [0.00,0.00] | -0.01 [-0.03,0.00] | 0.32 [-0.02,1.00] | -0.02 [-0.04,0.00] |

### Axis: `naturalness`

| Pair | en | hi | mr | te | kn | ta | bn |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini–sarvam | 0.01 [0.00,0.04] | 0.21 [0.06,0.36] | 0.05 [-0.05,0.17] | 0.04 [-0.06,0.14] | 0.09 [-0.01,0.21] | 0.17 [0.04,0.36] | -0.02 [-0.11,0.09] |

## Intra-judge Krippendorff's α across reruns
(Rating Roulette robustness check: higher = more rerun-consistent)

| Judge | attack_validity | equivalence | naturalness |
|---|---:|---:|---:|
| gemini | — | — | — |
| sarvam | — | — | — |

## Judge disagreements

Items where max-min across judges ≥ 2: **115** (of 600 × 3 = 1800 cell-axis pairs)

| Language | Axis | Attack vector | Disagreements |
|---|---|---|---:|
| bn | naturalness | direct | 10 |
| mr | naturalness | cultural_framing | 9 |
| ta | naturalness | cultural_framing | 9 |
| te | naturalness | code_switched | 8 |
| bn | naturalness | cultural_framing | 7 |
| en | naturalness | cultural_framing | 7 |
| kn | naturalness | code_switched | 7 |
| te | naturalness | cultural_framing | 7 |
| hi | naturalness | cultural_framing | 6 |
| kn | naturalness | cultural_framing | 6 |
| bn | naturalness | code_switched | 5 |
| mr | naturalness | code_switched | 5 |
| te | naturalness | direct | 5 |
| kn | naturalness | direct | 4 |
| hi | naturalness | code_switched | 3 |
| mr | naturalness | direct | 3 |
| ta | naturalness | code_switched | 3 |
| hi | equivalence | cultural_framing | 2 |
| hi | naturalness | direct | 2 |
| bn | attack_validity | cultural_framing | 1 |
| en | attack_validity | cultural_framing | 1 |
| kn | equivalence | code_switched | 1 |
| mr | attack_validity | cultural_framing | 1 |
| ta | equivalence | direct | 1 |
| ta | naturalness | direct | 1 |
| te | equivalence | cultural_framing | 1 |

Full per-item disagreement list: `panel_disagree.md`
