"""Generate paper-grade figures from finalized judgments.

Default: LLM judge (judgments_llm.jsonl) as primary source-of-truth (paper v2).
Pass --judge heuristic to use the heuristic judge (paper v1 / pre-flip).

Outputs to data/pilot/figures/ as PNG + matplotlib pdf.
"""
from __future__ import annotations
import argparse
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

FIGDIR = Path("data/pilot/figures")
FIGDIR.mkdir(parents=True, exist_ok=True)

LANG_ORDER = ["en", "hi", "mr", "te", "kn", "ta", "bn"]
LANG_LABELS = {"en": "English", "hi": "Hindi", "mr": "Marathi", "te": "Telugu",
               "kn": "Kannada", "ta": "Tamil", "bn": "Bengali"}
MODEL_ORDER = ["sarvam_105b", "sarvam_30b", "sarvam_m",
               "gpt_4o_mini", "gemini_25_flash", "llama_33_70b"]
MODEL_LABELS = {
    "sarvam_105b": "Sarvam-105B",
    "sarvam_30b": "Sarvam-30B",
    "sarvam_m": "Sarvam-m",
    "gpt_4o_mini": "GPT-4o-mini",
    "gemini_25_flash": "Gemini-2.5-Flash",
    "llama_33_70b": "Llama-3.3-70B",
}
ATTACK_ORDER = ["direct", "cultural_framing", "code_switched"]
ATTACK_LABELS = {"direct": "Direct", "cultural_framing": "Cultural Framing",
                 "code_switched": "Code-Switched"}


def load(judgments_path: Path):
    by_model_lang = defaultdict(lambda: {"refused": 0, "n": 0})
    by_model_attack = defaultdict(lambda: {"refused": 0, "n": 0})
    by_model_lang_attack = defaultdict(lambda: {"refused": 0, "n": 0})
    by_cat_lang = defaultdict(lambda: {"refused": 0, "n": 0})
    with open(judgments_path, encoding="utf-8") as f:
        for line in f:
            j = json.loads(line)
            r = j.get("refusal")
            if r is None:
                continue
            m, l, a, c = j["model_label"], j.get("language"), j.get("attack_vector"), j.get("category")
            by_model_lang[(m, l)]["refused"] += r
            by_model_lang[(m, l)]["n"] += 1
            by_model_attack[(m, a)]["refused"] += r
            by_model_attack[(m, a)]["n"] += 1
            by_model_lang_attack[(m, l, a)]["refused"] += r
            by_model_lang_attack[(m, l, a)]["n"] += 1
            by_cat_lang[(c, l)]["refused"] += r
            by_cat_lang[(c, l)]["n"] += 1
    return by_model_lang, by_model_attack, by_model_lang_attack, by_cat_lang


def fig1_model_lang_heatmap(by_model_lang):
    """Heatmap: refusal rate, model × language."""
    fig, ax = plt.subplots(figsize=(9, 4.5))
    Z = np.full((len(MODEL_ORDER), len(LANG_ORDER)), np.nan)
    for i, m in enumerate(MODEL_ORDER):
        for j, l in enumerate(LANG_ORDER):
            d = by_model_lang.get((m, l), {"refused": 0, "n": 0})
            if d["n"] > 0:
                Z[i, j] = d["refused"] / d["n"] * 100

    im = ax.imshow(Z, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(LANG_ORDER)))
    ax.set_xticklabels([LANG_LABELS[l] for l in LANG_ORDER], rotation=20, ha="right")
    ax.set_yticks(range(len(MODEL_ORDER)))
    ax.set_yticklabels([MODEL_LABELS[m] for m in MODEL_ORDER])
    for i in range(len(MODEL_ORDER)):
        for j in range(len(LANG_ORDER)):
            v = Z[i, j]
            if not np.isnan(v):
                color = "white" if v < 35 or v > 75 else "black"
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", color=color, fontsize=9)
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Refusal rate (%)")
    ax.set_title("Refusal Rate by Model × Language (n=500+ per Indic cell)")
    plt.tight_layout()
    plt.savefig(FIGDIR / "fig1_model_lang_heatmap.png", dpi=150)
    plt.savefig(FIGDIR / "fig1_model_lang_heatmap.pdf")
    plt.close()
    print(f"  fig1: {FIGDIR / 'fig1_model_lang_heatmap.png'}")


def fig2_attack_vector_effect(by_model_attack):
    """Bar chart: refusal rate by attack vector, per model."""
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(MODEL_ORDER))
    width = 0.27
    for k, av in enumerate(ATTACK_ORDER):
        rates = []
        for m in MODEL_ORDER:
            d = by_model_attack.get((m, av), {"refused": 0, "n": 0})
            r = d["refused"] / d["n"] * 100 if d["n"] > 0 else 0
            rates.append(r)
        ax.bar(x + (k - 1) * width, rates, width, label=ATTACK_LABELS[av])
    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_LABELS[m] for m in MODEL_ORDER], rotation=15, ha="right")
    ax.set_ylabel("Refusal rate (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Effect of Attack Vector on Refusal Rate, by Model")
    ax.legend(loc="upper right", framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIGDIR / "fig2_attack_vector_effect.png", dpi=150)
    plt.savefig(FIGDIR / "fig2_attack_vector_effect.pdf")
    plt.close()
    print(f"  fig2: {FIGDIR / 'fig2_attack_vector_effect.png'}")


def fig3_sister_script_telugu_kannada(by_model_lang):
    """Bar chart: Telugu vs Kannada per model, with shared-script reference."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(MODEL_ORDER))
    width = 0.35
    te_rates, kn_rates = [], []
    for m in MODEL_ORDER:
        te = by_model_lang.get((m, "te"), {"refused": 0, "n": 0})
        kn = by_model_lang.get((m, "kn"), {"refused": 0, "n": 0})
        te_rates.append(te["refused"] / te["n"] * 100 if te["n"] > 0 else 0)
        kn_rates.append(kn["refused"] / kn["n"] * 100 if kn["n"] > 0 else 0)
    ax.bar(x - width / 2, te_rates, width, label="Telugu", color="#3a7ca5")
    ax.bar(x + width / 2, kn_rates, width, label="Kannada", color="#ef8354")
    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_LABELS[m] for m in MODEL_ORDER], rotation=15, ha="right")
    ax.set_ylabel("Refusal rate (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Sister-Script Null Result: Telugu vs Kannada (related Brahmic scripts)")
    ax.legend(framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIGDIR / "fig3_sister_script.png", dpi=150)
    plt.savefig(FIGDIR / "fig3_sister_script.pdf")
    plt.close()
    print(f"  fig3: {FIGDIR / 'fig3_sister_script.png'}")


def fig4_reasoning_vs_legacy(by_model_lang):
    """Line chart: Sarvam-105B vs 30B vs m by language — reasoning amplification."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sarvam_models = ["sarvam_105b", "sarvam_30b", "sarvam_m"]
    colors = ["#1a5276", "#2980b9", "#aed6f1"]
    for m, color in zip(sarvam_models, colors):
        rates = []
        for l in LANG_ORDER:
            d = by_model_lang.get((m, l), {"refused": 0, "n": 0})
            rates.append(d["refused"] / d["n"] * 100 if d["n"] > 0 else 0)
        ax.plot(LANG_ORDER, rates, "o-", label=MODEL_LABELS[m], color=color, linewidth=2, markersize=8)
    ax.set_xticks(range(len(LANG_ORDER)))
    ax.set_xticklabels([LANG_LABELS[l] for l in LANG_ORDER], rotation=15, ha="right")
    ax.set_ylabel("Refusal rate (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Reasoning vs Legacy: Sarvam Family Per-Language Profile")
    ax.legend(framealpha=0.9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIGDIR / "fig4_reasoning_vs_legacy.png", dpi=150)
    plt.savefig(FIGDIR / "fig4_reasoning_vs_legacy.pdf")
    plt.close()
    print(f"  fig4: {FIGDIR / 'fig4_reasoning_vs_legacy.png'}")


def fig5_cultural_framing_by_lang(by_model_lang_attack):
    """Heatmap: cultural-framing minus direct (refusal drop), model × language."""
    fig, ax = plt.subplots(figsize=(9, 4.5))
    Z = np.full((len(MODEL_ORDER), len(LANG_ORDER)), np.nan)
    for i, m in enumerate(MODEL_ORDER):
        for j, l in enumerate(LANG_ORDER):
            d_direct = by_model_lang_attack.get((m, l, "direct"), {"refused": 0, "n": 0})
            d_cf = by_model_lang_attack.get((m, l, "cultural_framing"), {"refused": 0, "n": 0})
            if d_direct["n"] > 0 and d_cf["n"] > 0:
                Z[i, j] = (d_cf["refused"] / d_cf["n"] - d_direct["refused"] / d_direct["n"]) * 100

    vmax = max(abs(np.nanmin(Z)), abs(np.nanmax(Z)))
    im = ax.imshow(Z, cmap="RdBu", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(range(len(LANG_ORDER)))
    ax.set_xticklabels([LANG_LABELS[l] for l in LANG_ORDER], rotation=20, ha="right")
    ax.set_yticks(range(len(MODEL_ORDER)))
    ax.set_yticklabels([MODEL_LABELS[m] for m in MODEL_ORDER])
    for i in range(len(MODEL_ORDER)):
        for j in range(len(LANG_ORDER)):
            v = Z[i, j]
            if not np.isnan(v):
                color = "white" if abs(v) > vmax * 0.6 else "black"
                ax.text(j, i, f"{v:+.0f}", ha="center", va="center", color=color, fontsize=9)
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Δ Refusal rate (pp): cultural_framing − direct")
    ax.set_title("Cultural-Framing Attack Effect (negative = jailbreak success)")
    plt.tight_layout()
    plt.savefig(FIGDIR / "fig5_cultural_framing_effect.png", dpi=150)
    plt.savefig(FIGDIR / "fig5_cultural_framing_effect.pdf")
    plt.close()
    print(f"  fig5: {FIGDIR / 'fig5_cultural_framing_effect.png'}")


def make_disagreement_heatmap(by_model_lang_llm, by_model_lang_heur):
    """Figure 6: Δ between LLM and heuristic judge per (model × language)."""
    fig, ax = plt.subplots(figsize=(9, 4.5))
    Z = np.full((len(MODEL_ORDER), len(LANG_ORDER)), np.nan)
    for i, m in enumerate(MODEL_ORDER):
        for j, l in enumerate(LANG_ORDER):
            llm = by_model_lang_llm.get((m, l), {"refused": 0, "n": 0})
            heur = by_model_lang_heur.get((m, l), {"refused": 0, "n": 0})
            if llm["n"] > 0 and heur["n"] > 0:
                Z[i, j] = (llm["refused"] / llm["n"] - heur["refused"] / heur["n"]) * 100
    vmax = max(abs(np.nanmin(Z)), abs(np.nanmax(Z)))
    im = ax.imshow(Z, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(range(len(LANG_ORDER)))
    ax.set_xticklabels([LANG_LABELS[l] for l in LANG_ORDER], rotation=20, ha="right")
    ax.set_yticks(range(len(MODEL_ORDER)))
    ax.set_yticklabels([MODEL_LABELS[m] for m in MODEL_ORDER])
    for i in range(len(MODEL_ORDER)):
        for j in range(len(LANG_ORDER)):
            v = Z[i, j]
            if not np.isnan(v):
                color = "white" if abs(v) > vmax * 0.6 else "black"
                ax.text(j, i, f"{v:+.0f}", ha="center", va="center", color=color, fontsize=9)
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Δ refusal rate (pp): LLM judge − heuristic")
    ax.set_title("Measurement Crisis: Heuristic Undercounts Reasoning-Model Refusals in Indic Languages")
    plt.tight_layout()
    plt.savefig(FIGDIR / "fig6_measurement_crisis.png", dpi=150)
    plt.savefig(FIGDIR / "fig6_measurement_crisis.pdf")
    plt.close()
    print(f"  fig6: {FIGDIR / 'fig6_measurement_crisis.png'}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--judge", choices=["llm", "heuristic"], default="llm",
                   help="Which judge to treat as primary (default: llm)")
    args = p.parse_args()

    if args.judge == "llm":
        primary_path = Path("data/pilot/judgments_llm.jsonl")
        secondary_path = Path("data/pilot/judgments.jsonl")
    else:
        primary_path = Path("data/pilot/judgments.jsonl")
        secondary_path = Path("data/pilot/judgments_llm.jsonl")
    print(f"Primary judge: {primary_path.name}")
    by_model_lang, by_model_attack, by_model_lang_attack, by_cat_lang = load(primary_path)
    print(f"  loaded primary.")
    by_model_lang_alt, _, _, _ = load(secondary_path)
    print(f"  loaded secondary for disagreement plot.")
    print("Generating figures:")
    fig1_model_lang_heatmap(by_model_lang)
    fig2_attack_vector_effect(by_model_attack)
    fig3_sister_script_telugu_kannada(by_model_lang)
    fig4_reasoning_vs_legacy(by_model_lang)
    fig5_cultural_framing_by_lang(by_model_lang_attack)
    # Fig 6: LLM-vs-heuristic disagreement (only meaningful when llm is primary)
    if args.judge == "llm":
        make_disagreement_heatmap(by_model_lang, by_model_lang_alt)
    print("Done.")


if __name__ == "__main__":
    main()
