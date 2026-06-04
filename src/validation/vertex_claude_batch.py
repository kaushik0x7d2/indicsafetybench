"""
Claude judging via Vertex AI Batch Prediction — bypasses the per-base-model
online TPM quota that's currently 0 on this project for Anthropic models.

Pipeline:
    build  → assemble input JSONL (one line per item × axis)
    submit → upload to GCS, kick off Vertex BatchPredictionJob
    poll   → wait for completion (or check status)
    merge  → download output, parse, write standard-format judgments JSONL
    smoke  → 2-row end-to-end test

Usage:
    # Smoke first (2 rows, ~1 min on GCP, ~$0.001):
    python -m src.validation.vertex_claude_batch smoke

    # Full v3 (3,140 rows after dedup with prior Gemini/Sarvam runs):
    python -m src.validation.vertex_claude_batch build --out gs://indicsafetybench-judging/v3/claude_input.jsonl
    python -m src.validation.vertex_claude_batch submit --input gs://indicsafetybench-judging/v3/claude_input.jsonl
    python -m src.validation.vertex_claude_batch poll --job-name <NAME>
    python -m src.validation.vertex_claude_batch merge --output-prefix gs://indicsafetybench-judging/v3/claude_output/

Defaults:
    project   = GCP_PROJECT from .env
    region    = us-east5 (where Anthropic batch is available)
    model     = claude-sonnet-4-5@20250929
    bucket    = indicsafetybench-judging
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

PROJECT = os.getenv("GCP_PROJECT")
REGION = "us-east5"
MODEL_ID = "claude-sonnet-4-5@20250929"
BUCKET = "indicsafetybench-judging"
GCS_PREFIX = f"gs://{BUCKET}/v3"

OUT_DIR = Path("data/validation/panel")
JUDGE_ID = "claude_sonnet_45_vertex_batch"

# Reuse the rubric + sample loader from the existing judge panel
from src.validation.llm_judge_panel import (
    RUBRIC, LANG_NAMES, load_sample, attach_english_seed,
)


# -----------------------------------------------------------------------------
# build — emit input JSONL
# -----------------------------------------------------------------------------

def render_rubric(axis: str, item: dict) -> str:
    lang = item.get("language", "en")
    return RUBRIC[axis].format(
        language_name=LANG_NAMES.get(lang, lang.title()),
        language_name_upper=LANG_NAMES.get(lang, lang.title()).upper(),
        english_seed=(item.get("english_seed") or "")[:1500],
        prompt=(item.get("prompt") or "")[:2000],
        attack_vector=item.get("attack_vector", "direct"),
    )


def build_input_jsonl(items: list[dict], axes: list[str], out_path: str) -> int:
    """Write one JSON line per (item, axis), using Vertex Anthropic batch format.

    Each line is `{"request": {...Anthropic Messages params...}, "custom_id": "..."}`.
    The custom_id encodes (variant_id|axis) so we can join output back to items.
    """
    written = 0
    write_to_local = not out_path.startswith("gs://")
    if write_to_local:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        f = open(out_path, "w", encoding="utf-8")
    else:
        import io
        buf = io.StringIO()
        f = buf

    try:
        for item in items:
            for axis in axes:
                # Skip API call for direct + attack_validity (auto-N/A)
                if axis == "attack_validity" and item.get("attack_vector") == "direct":
                    continue
                custom_id = f"{item['variant_id']}|{axis}"
                rubric_text = render_rubric(axis, item)
                line = {
                    "custom_id": custom_id,
                    "request": {
                        "anthropic_version": "vertex-2023-10-16",
                        "messages": [{"role": "user", "content": rubric_text}],
                        "max_tokens": 1024,
                        "temperature": 0.3,
                    },
                }
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
                written += 1
    finally:
        if write_to_local:
            f.close()

    if not write_to_local:
        from google.cloud import storage
        text = buf.getvalue()
        bucket_name, blob_path = parse_gs(out_path)
        client = storage.Client(project=PROJECT)
        blob = client.bucket(bucket_name).blob(blob_path)
        blob.upload_from_string(text, content_type="application/jsonl")

    return written


def parse_gs(uri: str) -> tuple[str, str]:
    """gs://bucket/path → (bucket, path)"""
    m = re.match(r"gs://([^/]+)/(.+)$", uri)
    if not m:
        raise ValueError(f"not a gs:// URI: {uri}")
    return m.group(1), m.group(2)


# -----------------------------------------------------------------------------
# submit — create Vertex BatchPredictionJob
# -----------------------------------------------------------------------------

def submit_batch(input_uri: str, output_prefix: str, display_name: str) -> str:
    """Submit a BatchPredictionJob for the Anthropic publisher model.
    Returns the job resource name."""
    import vertexai
    from vertexai.batch_prediction import BatchPredictionJob

    vertexai.init(project=PROJECT, location=REGION)

    model_name = f"publishers/anthropic/models/{MODEL_ID}"
    print(f"Submitting batch job:")
    print(f"  model: {model_name}")
    print(f"  input: {input_uri}")
    print(f"  output prefix: {output_prefix}")

    job = BatchPredictionJob.submit(
        source_model=model_name,
        input_dataset=input_uri,
        output_uri_prefix=output_prefix,
        job_display_name=display_name,
    )
    job_name = job.resource_name
    print(f"Submitted job: {job_name}")
    print(f"State: {job.state.name}")
    return job_name


def poll_batch(job_name: str, interval_s: int = 30) -> str:
    """Poll a batch job until it reaches a terminal state. Returns final state."""
    import vertexai
    from vertexai.batch_prediction import BatchPredictionJob
    vertexai.init(project=PROJECT, location=REGION)

    job = BatchPredictionJob(job_name)
    terminal = {"JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED", "JOB_STATE_CANCELLED",
                "JOB_STATE_EXPIRED", "JOB_STATE_PARTIALLY_SUCCEEDED"}

    t_start = time.time()
    last_state = None
    while True:
        job.refresh()
        state = job.state.name
        if state != last_state:
            elapsed = int(time.time() - t_start)
            print(f"  [{elapsed}s] state: {state}", flush=True)
            last_state = state
        if state in terminal:
            print(f"\nFinal state: {state}")
            if state in ("JOB_STATE_FAILED", "JOB_STATE_EXPIRED"):
                print(f"Error: {getattr(job, 'error', '?')}")
            output_info = getattr(job, "output_location", None)
            if output_info:
                print(f"Output: {output_info}")
            return state
        time.sleep(interval_s)


# -----------------------------------------------------------------------------
# merge — download output, parse, write standard-format judgments JSONL
# -----------------------------------------------------------------------------

_JSON_RE = re.compile(r"\{[^{}]*\"score\"[^{}]*\}", re.DOTALL)


def parse_judge_response(text: str) -> tuple[Optional[int], str]:
    if not text:
        return None, ""
    for m in _JSON_RE.findall(text):
        try:
            j = json.loads(m)
            s = j.get("score")
            if s is None:
                continue
            return int(s), str(j.get("rationale", ""))[:200]
        except (json.JSONDecodeError, ValueError, TypeError):
            continue
    nums = [int(x) for x in re.findall(r"\b[0-5]\b", text)]
    if nums:
        return nums[0], text[:200]
    return None, text[:200]


def merge_batch_output(output_prefix: str, items_by_vid: dict[str, dict]):
    """Download all .jsonl files under output_prefix, parse responses, write
    one judgments_<judge>_<axis>.jsonl per axis in OUT_DIR."""
    from google.cloud import storage

    bucket_name, prefix = parse_gs(output_prefix)
    client = storage.Client(project=PROJECT)
    bucket = client.bucket(bucket_name)

    # List output files; Vertex writes predictions to one or more JSONL files
    blobs = [b for b in bucket.list_blobs(prefix=prefix) if b.name.endswith(".jsonl")]
    print(f"Found {len(blobs)} output JSONL files under {output_prefix}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    by_axis_writers: dict[str, "io.TextIOBase"] = {}
    def writer_for(axis: str):
        if axis not in by_axis_writers:
            p = OUT_DIR / f"judgments_{JUDGE_ID}_{axis}.jsonl"
            by_axis_writers[axis] = open(p, "a", encoding="utf-8")
        return by_axis_writers[axis]

    success = failed = 0
    for blob in blobs:
        text = blob.download_as_text()
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                failed += 1
                continue
            cid = rec.get("custom_id") or rec.get("request", {}).get("custom_id")
            if not cid:
                # Try to extract from request body or skip
                failed += 1
                continue
            vid, axis = cid.split("|", 1)
            item = items_by_vid.get(vid)
            if not item:
                failed += 1
                continue
            # Find response content - Vertex Anthropic batch format
            resp = rec.get("response") or {}
            content_blocks = resp.get("content") or []
            text_out = ""
            for b in content_blocks:
                if isinstance(b, dict) and b.get("type") == "text":
                    text_out += b.get("text", "")
            if not text_out and rec.get("status") != "JOB_STATE_SUCCEEDED":
                # Status / error level
                failed += 1
                continue
            score, rationale = parse_judge_response(text_out)
            out_rec = {
                "variant_id": vid,
                "seed_id": item.get("seed_id"),
                "language": item.get("language"),
                "attack_vector": item.get("attack_vector"),
                "category": item.get("category"),
                "judge_id": "sonnet",
                "judge_model": MODEL_ID,
                "axis": axis,
                "rerun_idx": 0,
                "temperature": 0.3,
                "score": score,
                "rationale": rationale,
                "parse_ok": score is not None,
                "raw": text_out[:400],
                "via": "vertex_batch_prediction",
                "ts": time.time(),
            }
            writer_for(axis).write(json.dumps(out_rec, ensure_ascii=False) + "\n")
            if score is not None:
                success += 1
            else:
                failed += 1

    for w in by_axis_writers.values():
        w.close()
    print(f"Parsed: success={success}  parse_fail={failed}")
    print(f"Wrote: {sorted([f'judgments_{JUDGE_ID}_{ax}.jsonl' for ax in by_axis_writers])}")


# -----------------------------------------------------------------------------
# CLI subcommands
# -----------------------------------------------------------------------------

def load_corpus(languages: list[str], limit: Optional[int]) -> list[dict]:
    items = attach_english_seed(load_sample(languages))
    if limit:
        capped = []
        per_lang = {}
        for v in items:
            lang = v.get("language", "en")
            n = per_lang.get(lang, 0)
            if n >= limit:
                continue
            capped.append(v)
            per_lang[lang] = n + 1
        items = capped
    return items


def cmd_build(args):
    items = load_corpus(args.languages, args.limit)
    n = build_input_jsonl(items, args.axes, args.out)
    print(f"Wrote {n} request lines -> {args.out}")


def cmd_submit(args):
    job_name = submit_batch(args.input, args.output_prefix,
                            display_name=args.name)
    state_file = Path("data/validation/panel/_last_vertex_batch_job.txt")
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(job_name, encoding="utf-8")
    print(f"Saved job name to {state_file}")


def cmd_poll(args):
    job_name = args.job_name
    if not job_name:
        state_file = Path("data/validation/panel/_last_vertex_batch_job.txt")
        if state_file.exists():
            job_name = state_file.read_text().strip()
    if not job_name:
        print("ERROR: --job-name not given and no _last_vertex_batch_job.txt found")
        return 1
    final_state = poll_batch(job_name, interval_s=args.interval)
    return 0 if final_state in ("JOB_STATE_SUCCEEDED", "JOB_STATE_PARTIALLY_SUCCEEDED") else 1


def cmd_merge(args):
    items = load_corpus(args.languages, args.limit)
    by_vid = {it["variant_id"]: it for it in items}
    merge_batch_output(args.output_prefix, by_vid)


def cmd_smoke(args):
    """End-to-end 2-row smoke. Validates the batch bypass hypothesis."""
    print("=== SMOKE TEST ===  2-row Vertex Anthropic batch")
    items = load_corpus(["te"], limit=2)
    print(f"Loaded {len(items)} Telugu items for smoke")

    input_path = f"{GCS_PREFIX}/smoke/claude_input_smoke.jsonl"
    output_prefix = f"{GCS_PREFIX}/smoke/output/"
    n = build_input_jsonl(items, ["naturalness"], input_path)
    print(f"Built {n} input rows -> {input_path}")

    job_name = submit_batch(input_path, output_prefix,
                            display_name="isb-claude-smoke")
    print()
    state = poll_batch(job_name, interval_s=20)
    if state != "JOB_STATE_SUCCEEDED":
        print(f"\nSMOKE FAILED with state {state}")
        return 1

    # Merge
    print()
    by_vid = {it["variant_id"]: it for it in items}
    # Find actual output dir from job
    import vertexai
    from vertexai.batch_prediction import BatchPredictionJob
    vertexai.init(project=PROJECT, location=REGION)
    job = BatchPredictionJob(job_name)
    actual_output = getattr(job, "output_location", None) or output_prefix
    print(f"Job output: {actual_output}")
    merge_batch_output(actual_output, by_vid)
    print("\nSMOKE PASSED — Vertex batch bypass works.")
    return 0


def main():
    if not PROJECT:
        print("ERROR: GCP_PROJECT not set in .env")
        return 1

    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    pb = sub.add_parser("build", help="emit batch input JSONL")
    pb.add_argument("--languages", nargs="+", default=["bn","en","hi","kn","mr","ta","te"])
    pb.add_argument("--axes", nargs="+", default=["naturalness","equivalence","attack_validity"])
    pb.add_argument("--limit", type=int, default=None, help="per-language cap")
    pb.add_argument("--out", default=f"{GCS_PREFIX}/claude_input.jsonl")
    pb.set_defaults(func=cmd_build)

    ps = sub.add_parser("submit", help="submit BatchPredictionJob")
    ps.add_argument("--input", required=True)
    ps.add_argument("--output-prefix", default=f"{GCS_PREFIX}/claude_output/")
    ps.add_argument("--name", default="isb-claude-judge")
    ps.set_defaults(func=cmd_submit)

    pp = sub.add_parser("poll", help="poll job to completion")
    pp.add_argument("--job-name", default=None)
    pp.add_argument("--interval", type=int, default=30)
    pp.set_defaults(func=cmd_poll)

    pm = sub.add_parser("merge", help="download + parse output → standard JSONL")
    pm.add_argument("--output-prefix", required=True)
    pm.add_argument("--languages", nargs="+", default=["bn","en","hi","kn","mr","ta","te"])
    pm.add_argument("--limit", type=int, default=None)
    pm.set_defaults(func=cmd_merge)

    psm = sub.add_parser("smoke", help="2-row end-to-end smoke test")
    psm.set_defaults(func=cmd_smoke)

    args = p.parse_args()
    return args.func(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
