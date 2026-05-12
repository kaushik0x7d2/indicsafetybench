# IndicSafetyBench — Paper Source

This directory contains the LaTeX source for the IndicSafetyBench paper (draft v2).

## Files

- `paper.tex` — main manuscript (~8 pages of content + appendix). Uses `article` class with `natbib`. Conference-template-agnostic — can be ported to ACL/EMNLP/NeurIPS by swapping the preamble.
- `references.bib` — bibliography (BibTeX format, ~30 entries).
- `figures/` — copies of the 6 paper figures from `../data/pilot/figures/`.

## Compile locally (MiKTeX / TeX Live)

```bash
cd paper
pdflatex paper.tex
bibtex paper
pdflatex paper.tex
pdflatex paper.tex   # twice more for cross-references
```

Output: `paper.pdf`.

## Push to Overleaf

### Option A — Manual upload (~5 min)
1. Sign in to Overleaf.
2. *New Project → Upload Project*.
3. Zip `paper.tex`, `references.bib`, and `figures/` and upload.
4. Overleaf will auto-compile. Set `paper.tex` as the main document.

### Option B — "Open in Overleaf" deep-link
After this directory is published on GitHub (the repo is private currently — make a public mirror or copy `paper/` to a public repo first), use:

```
https://www.overleaf.com/docs?snip_uri=https://raw.githubusercontent.com/kaushik0x7d2/indicsafetybench/main/paper/paper.tex&snip_uri=https://raw.githubusercontent.com/kaushik0x7d2/indicsafetybench/main/paper/references.bib
```

The figures won't auto-import via deep link — upload them manually after.

### Option C — Drop into an ACL/EMNLP template
1. From Overleaf gallery, open *ACL 2026* or *EMNLP 2024* template.
2. Paste `paper.tex` content (skip the `\documentclass` and `\begin{document}` lines, keep the body).
3. Paste `references.bib` content.
4. Upload `figures/*.png`.
5. Compile.

## Conventions used

- Citations are `\citep{key}` and `\citet{key}` (natbib).
- Tables use `booktabs` (\toprule/\midrule/\bottomrule).
- Figures use `\columnwidth` and `graphicspath{{figures/}}`.
- All numbers come from `data/pilot/PILOT_REPORT.md`, `STATS_REPORT.md`, and `judge_agreement_report.md`. To verify, run:
  ```
  python -m src.paper.stats
  python -m src.paper.make_figures
  ```

## Status

Draft v2 — LLM-judge-primary spine. Pre-Sumanth review. The `[HUMAN-VAL]` placeholders in `paper-draft-v2.md` (in the NYU planning folder) will be filled in by author native-speaker validation results (see `VALIDATION_TE.md` in the project root).

## Submission targets

- **arXiv** (preprint, target May 2026)
- **NeurIPS Datasets & Benchmarks Workshop** (Indic NLP / AI Safety)
- **EACL/EMNLP Long Paper 2026** (8-page format)
