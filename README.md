# IndicSafetyBench

A multilingual safety benchmark for Indian-language LLMs with reasoning-architecture comparison.

**Status:** Pre-publication. Pilot v3 complete. Target arXiv preprint May 2026.

**Author:** Kaushik Kachireddy (NYU Tandon, MS Emerging Technologies, Fall 2026 cohort)

**Endorser:** Sumanth Doddapaneni (Sarvam AI / AI4Bharat / IIT Madras) — arXiv-only, not co-author.

---

## What this is

A pilot safety benchmark covering:

- **7 languages:** English baseline + 6 Indic languages (Hindi, Marathi, Telugu, Kannada, Tamil, Bengali)
- **8 harm categories:** violence/weapons, self-harm, CSAM-adjacent, privacy/doxxing, hate speech (with caste/religious sub-categories), misinformation, cybercrime, sexual exploitation
- **3 attack vectors:** direct, cultural-framing (Indian persona impersonation), code-switching (Hinglish/Tanglish/etc.)
- **6 target models:** Sarvam-105B/30B/m (Sarvam AI), GPT-4o-mini, Gemini-2.5-Flash, Llama-3.3-70B
- **Dual judge:** heuristic regex classifier + Gemini-2.5-Flash LLM-as-judge, with Cohen's κ inter-judge agreement

### Scale (pilot v3)
- 425 English seeds (167 deployed in pilot)
- 3,340 variants
- 20,040 model inferences
- 19,423 dual-judge labeled pairs
- 5 paper-grade figures
- Bootstrap 95% CIs on all key cells

## Key findings

1. **Sarvam reasoning models (30B/105B) maintain 85-92% refusal rate** uniformly across all 7 languages — **but heuristic safety classifiers systematically undercount their refusals** (Δ up to 60pp) because they produce nuanced soft-refusals ("I cannot help with X, but here are safer alternatives") that regex classifiers miscount as engagement.

2. **Reasoning architecture is robust to cultural-framing attacks.** Sarvam-30B/105B: -2 to -3pp refusal drop under Indian-journalist/professor/NGO persona attacks (95% CI crosses zero). Non-reasoning models drop -15 to -28pp (CIs entirely below zero).

3. **Llama-3.3-70B is genuinely catastrophic in Indic safety** — 38-54% Indic refusal rate (LLM judge), confirmed by both judges.

4. **Sister-script null result.** Telugu and Kannada share Brahmic visual heritage but show divergent safety profiles per model. Models read language identity, not script visual similarity.

5. **Per-cell Cohen's κ between heuristic and LLM judge degrades sharply for reasoning models in Dravidian languages** (κ=0.07-0.17 for Sarvam-105B/30B in Tamil/Bengali). This is a methodological finding: prior heuristic-based Indic safety benchmarks may have systematically underreported reasoning-model safety.

## Repository structure

```
indicsafetybench/
├── src/
│   ├── providers/          # Sarvam + OpenRouter API clients
│   ├── translation/        # Indic translation pipeline
│   ├── attacks/            # Cultural-framing + code-switching generators
│   ├── seeds/              # Seed → multilingual test_set expansion
│   ├── pilot/              # Pilot runner, judges, metrics
│   └── paper/              # Figures + statistics
├── data/
│   ├── seeds/              # English source seeds (425, 8 categories)
│   ├── expanded/           # Per-category multilingual test sets
│   ├── pilot/
│   │   ├── test_set.json   # Master 3,340-variant test set
│   │   ├── responses/      # Per-model JSONL responses
│   │   ├── judgments.jsonl # Heuristic judge labels
│   │   ├── judgments_llm.jsonl # LLM judge labels
│   │   ├── figures/        # Paper figures (PNG + PDF)
│   │   ├── PILOT_REPORT.md # Full metrics
│   │   ├── STATS_REPORT.md # Bootstrap CIs + odds ratios
│   │   └── judge_agreement_report.md
│   └── seeds_v2/           # Additional 210 seeds (cybercrime/hate/self_harm)
├── pyproject.toml
└── README.md
```

## Reproducing the pilot

### Setup

```bash
python -m venv .venv
.venv/Scripts/activate    # Windows PowerShell
# source .venv/bin/activate  # Linux/macOS
pip install -e ".[dev]"

cp .env.example .env
# Fill SARVAM_API_KEY (free) + OPENROUTER_API_KEY ($25 budget recommended)
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

# 6. Statistics + figures
python -m src.pilot.metrics
python -m src.paper.stats
python -m src.paper.make_figures
```

## Ethics & responsible disclosure

This benchmark contains adversarial prompts that, if responded to permissively, would produce harmful content. We follow the responsible-disclosure norms established by HarmBench, AdvBench, and IndicJR:

- Adversarial prompts in this repo are research artifacts intended for safety evaluation only.
- Model responses to harmful prompts are not redistributed beyond aggregate statistics.
- Prior to public release, we coordinate disclosure with relevant model providers (Sarvam AI in particular).
- Future public release will be **gated** — researchers requesting raw seeds + responses will require institutional attestation, following HarmBench precedent.

This repository is currently **private** pending publication.

## Concurrent prior work

- **IndicJR** (Pattnayak et al., EACL 2026) — 45k prompts × 12 langs × 12 models. Foundational. Tests Sarvam-1 (older non-reasoning).
- **IndicSafe** (Pattnayak et al., 2026) — 9 culturally-grounded harm categories, 6k prompts.
- **XL-SafetyBench** (Choi et al., arXiv:2605.05662, May 2026) — Concurrent. Tests Sarvam-30B + Sarvam-105B on Hindi only.
- **AILuminate v1.0 Hindi** (MLCommons/Tattle, 2025-26) — Industry-standard, Hindi-only.

## License

- **Code:** Apache License 2.0 (see `LICENSE`)
- **Data:** No public license at this stage. Gated-release policy TBD.

## Citation (placeholder)

```bibtex
@misc{kachireddy2026indicsafetybench,
  title  = {IndicSafetyBench: Per-Language Safety Profiles of Indian-Language LLMs and a Measurement Crisis in Reasoning-Model Refusals},
  author = {Kachireddy, Kaushik},
  year   = {2026},
  note   = {Preprint in preparation},
  url    = {https://github.com/kaushik0x7d2/indicsafetybench}
}
```

## Contact

- Repository: kaushik0x7d2/indicsafetybench (private until preprint)
- Open an issue or DM @kaushik0x7d2 for collaboration inquiries.

---

*Pre-publication. Do not distribute without permission.*
