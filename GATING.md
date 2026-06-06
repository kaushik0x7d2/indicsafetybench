# Gated-access policy for IndicSafetyBench raw artifacts

This document is the public-facing access policy referenced in `paper.tex` §1, §3, and §7 (Ethics).

## What is publicly released without gating

The following artifacts are released under permissive terms with no access request required:

| Artifact | License |
|---|---|
| All code (`src/`, `scripts/`, `tools/`) | Apache 2.0 |
| Paper PDF and source (`paper/paper.{pdf,tex}`, `references.bib`) | CC BY 4.0 |
| Aggregate per-cell statistics (`data/pilot/STATS_REPORT.md`, `data/pilot/PILOT_REPORT.md`, `data/validation/PANEL_REPORT.md`, `data/validation/panel_kappa.jsonl`, `data/validation/panel_disagree.md`) | CC BY 4.0 |
| Judge-prompt rubrics and bootstrap seeds | CC BY 4.0 |
| LLM judgment JSONLs at the (variant_id, judge, axis, score) granularity (`data/validation/panel/judgments_*.jsonl`) | CC BY-NC 4.0 |
| Seed-prompt metadata (id, category, subcategory, framing, language) | CC BY 4.0 |

## What is GATED

The following artifacts require an access request because they consist of (a) operational details of adversarial prompts in Indic-language safety-research contexts, or (b) full model responses that, if redistributed permissively, would provide a one-stop training corpus for circumventing Indic safety RLHF:

| Artifact | Gate level |
|---|---|
| Raw English seed prompts in the 8 adversarial harm categories (`data/seeds/*.json` `prompts[*].text` field) | Attestation gate |
| Raw multilingual prompt variants per (seed, language, attack-vector) (`data/pilot/test_set.json` `prompts[*].text` field; `data/expanded/*/`) | Attestation gate |
| Raw model responses (`data/pilot/responses/*.jsonl` `response` field) | Attestation gate |
| Per-rater contaminated validation CSVs (`data/validation/{te,ta,mr,kn}/validator*_*.csv`) | Attestation gate + redaction commitment |

## How to request gated access

Email the custodian (see below) with:

1. **Researcher identity.** Full name, institutional affiliation, ORCID or institutional email.
2. **Use case.** A 200--400 word description of the research question, why aggregate statistics are insufficient, and what artifacts you specifically need.
3. **Attestation** (verbatim):

   > I attest that I will (a) use the gated IndicSafetyBench artifacts solely for safety-evaluation research, (b) not redistribute the gated artifacts to third parties or post them publicly, (c) not use the gated artifacts to train or fine-tune any model intended for deployment, (d) treat any verbatim per-rater quotes or per-rater identifying details in the contaminated validation CSVs as personally-identifiable and not republish them in any form, and (e) cite IndicSafetyBench (Kachireddy, 2026) in any published work that uses these artifacts.

4. **Affiliation verification.** A reply from your institutional email confirming (1)--(3); or a co-signed letter from a department head / advisor / institutional research office for student requests.

## Custodian and response time

- **Custodian:** Kaushik Kachireddy (first author).
- **Contact channel:** Listed on the project's public GitHub repository.
- **Target response time:** 10 business days from receipt of a complete request. Requests with incomplete information will be returned with a checklist within 3 business days.
- **Appeals:** If a request is declined, the requester may resubmit with additional context. An advisory review by an external safety-research peer is invoked for any appeal.

## What declines look like

Requests will be declined if:
- The proposed use is product development or competitive intelligence rather than safety research.
- The attestation is not signed verbatim.
- The institutional verification is from a free-tier mail provider with no institutional anchor.
- The requester has previously violated a similar gating attestation at HarmBench, AdvBench, IndicJR, IndicSafe, AILuminate, or any comparable benchmark.

## Versioning

This document is the **v1** of the gating policy and is committed alongside the v3 paper draft. Future revisions will be in `GATING.md` with the version tagged in the document's title.

Last updated: 2026-06-04.
