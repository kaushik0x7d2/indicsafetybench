# IndicSafetyBench

A pilot multilingual safety benchmark for Indian-language LLMs with a within-family reasoning-architecture comparison.

**Status:** Preprint, June 2026. See `paper/paper.pdf`.

**Author:** Kaushik Kachireddy (Independent Researcher)

---

## What this is

A pilot safety benchmark covering:

- **7 languages:** English baseline + 6 Indic languages (Hindi, Marathi, Telugu, Kannada, Tamil, Bengali)
- **8 harm categories:** violence/weapons, self-harm, CSAM-adjacent, privacy/doxxing, hate speech (with caste/religious sub-categories), misinformation, cybercrime, sexual exploitation
- **3 attack vectors:** direct, cultural-framing (Indian persona impersonation), code-switching (Hinglish/Tanglish/etc.)
- **6 target models:** Sarvam-105B/30B/m (Sarvam AI), GPT-4o-mini, Gemini-2.5-Flash, Llama-3.3-70B
- **Partial pilot:** `gpt-oss-120b` (OpenAI open-weight, via Ola Krutrim Cloud, n=200 stratified)
- **Dual judge:** heuristic regex classifier + Gemini-2.5-Flash LLM-as-judge, with Cohen's κ inter-judge agreement per cell
- **Cross-vendor sensitivity check:** Anthropic Claude (claude-opus-4-7) as independent third refusal judge on Sarvam-105B across all 7 languages (n=457 successful labels)

### Scale

- 425 English seeds (167 deployed in the pilot; the remaining 258 are released for downstream researchers)
- 3,340 multilingual variants
- 20,400 model inferences
- 20,268 dual-judge labelled pairs
- 5 paper-grade figures
- Bootstrap 95% CIs on all key cells (paired-bootstrap on cultural-framing Δ)

## Headline findings

1. **(C1) Heuristic safety classifiers systematically undercount Sarvam reasoning-model refusals by up to 60 pp in Dravidian languages and Bengali**, because these models produce structurally consistent soft-refusal patterns ("I cannot help with X, but here are safer alternatives") that regex classifiers miscount as engagement. Per-cell Cohen's κ collapses to **0.07–0.13** for Sarvam-105B/30B in Tamil and Bengali while remaining at **0.51–0.83** in English and Hindi.

2. **(C2) Under LLM judging, Sarvam reasoning models refuse at 82–96% across all seven languages** (Sarvam-105B: 91–96%; Sarvam-30B: 82–91%). An independent Anthropic Claude judge on Sarvam-105B agrees with Gemini on **96.9%** of items across all 7 languages (per-language range 93–100%), with Claude marginally **stricter** than Gemini — ruling out a Gemini-leniency hypothesis.

3. **(C3) Reasoning architecture is robust to Indian-persona cultural-framing attacks within our corpus** (with explicit ceiling-effect caveat). Non-reasoning models drop −16 to −31 pp under cultural framing (95% paired-bootstrap CI entirely below zero); Sarvam reasoning models show no detectable effect.

4. **(C4) Llama-3.3-70B is the catastrophic model in our suite** — Indic refusal rate 38–54% (LLM judge), confirmed by both judges.

5. **(C5) An independent orthographic failure mode of heuristic safety classifiers.** OpenAI's `gpt-oss-120b` refuses at 95–100% but the ASCII-only heuristic catches **zero** of its refusals — 91% of them use the typographic U+2019 apostrophe (`I'm sorry, but I can't help`) that ASCII anchor banks miss. A three-line regex patch lifts recall to 98%. Mechanically independent of the Sarvam soft-refusal pattern (C1).

## Repository structure

```
indicsafetybench/
├── paper/
│   ├── paper.tex                 # Final paper source (LaTeX)
│   ├── paper.pdf                 # 21 pages, two-column
│   ├── references.bib
│   └── figures/                  # 5 PNGs referenced by paper
│
├── src/
│   ├── providers/                # API clients (Sarvam, OpenRouter, Vertex, Prime Intellect, Krutrim)
│   ├── seeds/                    # Seed → multilingual test_set expansion
│   ├── pilot/                    # Pilot runner, judges (heuristic + LLM), metrics
│   ├── validation/               # Two-judge corpus-validation ensemble (Gemini-Pro × Sarvam-30B)
│   └── paper/                    # Bootstrap + paired-bootstrap statistics, figures
│
├── scripts/                      # Build / orchestration helpers
│
├── data/
│   ├── seeds/                    # 425 English seed metadata (text field gated per GATING.md)
│   ├── pilot/
│   │   ├── PILOT_REPORT.md       # Aggregate per-cell metrics
│   │   ├── STATS_REPORT.md       # Bootstrap CIs, paired-bootstrap CF Δ
│   │   ├── judgments_auto.jsonl  # Heuristic labels
│   │   ├── judgments_llm.jsonl   # LLM-judge labels (Gemini-2.5-Flash)
│   │   ├── uncertain_for_review.jsonl
│   │   ├── responses/            # Per-model JSONL responses (response field gated)
│   │   └── figures/
│   └── validation/
│       ├── PANEL_REPORT.md       # Likert means + Cohen κ + bootstrap CIs (corpus-validation)
│       ├── PANEL_KRIPPENDORFF.md # Krippendorff α (interval)
│       ├── panel/                # Per-call judge records (Gemini-Pro, Sarvam-30B)
│       └── claude_judge_v4_consolidated.json  # Cross-vendor sensitivity check (Appendix M)
│
├── docs/
│   ├── VALIDATION_PROTOCOL.md    # Likert questionnaire + LLM-judge rubric specs
│   └── FUNDING_REQUEST.md
│
├── GATING.md                     # Access policy for gated raw artifacts
├── LICENSE                       # Apache 2.0 (code); paper is CC BY 4.0
├── pyproject.toml
└── README.md
```

## What's publicly released vs gated

| Tier | Artifacts |
|---|---|
| **Public, no gate** | All code (`src/`, `scripts/`), paper PDF + source, aggregate statistics (`*_REPORT.md`), judge-prompt rubrics, bootstrap seeds, LLM judgment JSONLs at the `(variant_id, judge, axis, score)` granularity, seed metadata (id, category, etc.) |
| **Public, CC BY-NC 4.0** | LLM judgment JSONLs |
| **Gated (attestation required)** | Raw English seed prompts text, raw multilingual variants text, raw model responses text |

See `GATING.md` for the access-request procedure.

## Reproducing the pilot

### Setup

```bash
python -m venv .venv
.venv/Scripts/activate         # Windows PowerShell
# source .venv/bin/activate    # Linux/macOS
pip install -e ".[dev]"

cp .env.example .env
# Fill SARVAM_API_KEY (free Sarvam tier) + OPENROUTER_API_KEY (~$25 OpenRouter budget)
# Optional: GCP_PROJECT, GOOGLE_API_KEY, KRUTRIM_API_KEY, PI_API_KEY
```

### Pipeline (top-level commands)

```bash
# 1. Generate multilingual test set from English seeds
python -m src.seeds.expand --category cybercrime --all-langs --max-seeds 22
# ... repeat per category

# 2. Run target models against test set (resume-safe)
python -m src.pilot.run_pilot --model sarvam-105b
python -m src.pilot.run_pilot --model openai/gpt-4o-mini

# 3. Heuristic refusal classification
python -m src.pilot.auto_judge
python -m src.pilot.finalize_judgments

# 4. LLM-as-judge (Gemini-2.5-Flash via OpenRouter)
python -m src.pilot.llm_judge

# 5. Inter-judge agreement (Cohen's κ)
python -m src.pilot.compare_judges

# 6. Corpus-validation panel (Gemini-2.5-Pro × Sarvam-30B, 600 items × 3 axes)
python -m src.validation.llm_judge_panel
python -m src.validation.aggregate_panel

# 7. Cross-vendor sensitivity check (Claude on Sarvam-105B across 7 langs)
python scripts/build_v4_samples.py
python scripts/build_claude_wf_generic.py data/validation/<sample>.json 100 v4-<name>
# (then dispatch the resulting workflow scripts via Claude Code workflows)

# 8. Statistics + figures
python -m src.pilot.metrics
python -m src.paper.stats            # bootstrap + paired-bootstrap CIs
python -m src.paper.make_figures
```

## Ethics & responsible disclosure

This benchmark contains adversarial prompts that, if responded to permissively, would produce harmful content. We follow the responsible-disclosure norms established by HarmBench, AdvBench, and IndicJR:

- Adversarial prompts in this repo are research artifacts intended for safety evaluation only.
- Model responses to harmful prompts are not redistributed beyond aggregate statistics.
- Raw seeds and responses are gated per `GATING.md` — researchers requesting raw artifacts attest to safety-research-only use.
- The 200 `gpt-oss-120b` responses underlying the orthographic finding (C5) were obtained via the Ola Krutrim Cloud inference API under their Acceptable Use Policy; aggregate statistics are released, raw responses are not.

## Concurrent prior work

- **IndicJR** (Pattnayak & Chowdhuri, EACL 2026) — 45k prompts × 12 langs × 12 models.
- **IndicSafe** (Pattnayak & Chowdhuri, 2026) — 9 culturally-grounded harm categories, 6k prompts.
- **XL-SafetyBench** (Choi et al., arXiv:2605.05662, 2026) — Concurrent. Tests Sarvam-30B + Sarvam-105B on Hindi only.
- **AILuminate v1.0 Hindi** (Ghosh et al., MLCommons/Tattle, 2025) — Hindi-only.

## License

- **Code:** Apache License 2.0 (`LICENSE`)
- **Paper PDF + source + aggregate statistics:** CC BY 4.0
- **LLM judgment JSONLs:** CC BY-NC 4.0
- **Gated raw artifacts:** attestation required per `GATING.md`

## Citation

```bibtex
@misc{kachireddy2026indicsafetybench,
  title  = {IndicSafetyBench: Per-Language Safety Profiles of Indian-Language LLMs and a Measurement Crisis in Reasoning-Model Refusals},
  author = {Kachireddy, Kaushik},
  year   = {2026},
  url    = {https://github.com/kaushik0x7d2/indicsafetybench}
}
```

## Contact

Open an issue or DM `@kaushik0x7d2` for collaboration inquiries or to request gated access (see `GATING.md`).
