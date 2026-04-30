"""Bonus 2 comparative analysis runner.

Runs the SAME natural-language prompts through all 4 sandboxes and writes
a JSON report capturing latency, success, output kind, and notes. The
human-written comparative report in /doc consumes this JSON.

Usage:
    python src/run_comparative_analysis.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from code_generator import generate_python_code
from config import get_config
from sandboxes import SANDBOXES

# Subset of assignment prompts -- one per category for the report.
PROMPTS = [
    "Which Hugging Face model repo has the highest number of Community Discussions created?",
    "Create a table of the total number of Discussions created for every repo for every day of the week (Monday-Sunday).",
    "Which day of the week has the highest number of total Discussions created across all tracked Hugging Face repos?",
    "Bar chart: Likes count for every Model ID.",
    "Pie chart: % distribution of total Discussions belonging to each model.",
    "Stacked bar chart: open vs closed Discussions for every Model.",
]


def main() -> dict:
    cfg = get_config()
    if not cfg.has_openai:
        raise SystemExit("OPENAI_API_KEY required.")

    report = {"prompts": []}
    for prompt in PROMPTS:
        print(f"\n=== PROMPT: {prompt}")
        t0 = time.time()
        generated = generate_python_code(prompt)
        gen_t = time.time() - t0

        prompt_record = {
            "prompt": prompt,
            "code_generation_seconds": round(gen_t, 3),
            "code_chars": len(generated.code),
            "runs": [],
        }
        for label, cls in SANDBOXES.items():
            sandbox = cls()
            print(f"  -> {label}")
            res = sandbox.run(generated.code, cfg.database_url)
            prompt_record["runs"].append({
                "backend": res.backend,
                "label": label,
                "ok": res.ok,
                "elapsed_seconds": round(res.elapsed_seconds, 3),
                "stdout_len": len(res.stdout or ""),
                "stderr_len": len(res.stderr or ""),
                "notes": res.notes,
                "stderr_preview": (res.stderr or "")[:300],
            })
        report["prompts"].append(prompt_record)

    out_path = Path(__file__).resolve().parent.parent / "doc" / "comparative_analysis.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport written to {out_path}")
    return report


if __name__ == "__main__":
    main()
