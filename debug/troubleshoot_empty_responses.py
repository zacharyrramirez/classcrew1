"""
Local troubleshooting tool for empty AI responses.

What it does:
- Loads final PDFs from data/final_pdfs/<assignment_id>/
- Extracts text locally (no Canvas calls)
- Sends a grading request using OpenAIGrader with a minimal rubric
- Records per-file diagnostics (word counts, prompt size, outcome)
- Saves raw model output for inspection in data/debug_outputs/

Usage:
  python debug/troubleshoot_empty_responses.py <assignment_id> [--model=gpt-4o-mini] [--max_words=4000] [--limit=N]

Notes:
- Set environment variable DEBUG_MODE=1 for verbose logs
- This script NEVER posts to Canvas
"""

import os
import sys
import glob
import json
from typing import List, Dict, Any

from grader.grader import OpenAIGrader
from utils.file_ops import extract_text_from_pdf
from utils.config import FINAL_PDFS_DIR


def load_minimal_rubric() -> List[Dict[str, Any]]:
    """A simple 3-criterion rubric matching the screenshots the user shared."""
    return [
        {
            "criterion": "AI-Generated Interview Script",
            "max_points": 10,
            "description": "Quality, relevance, and completeness of the interview script."
        },
        {
            "criterion": "Critique of Tool",
            "max_points": 15,
            "description": "Thoughtful critique with strengths, weaknesses, and improvements."
        },
        {
            "criterion": "Submission Structure & Clarity",
            "max_points": 5,
            "description": "Organization, headings, clarity, and readability."
        },
    ]


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def truncate_words(text: str, max_words: int) -> str:
    if max_words <= 0:
        return text
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + f"\n\n[Truncated to first {max_words} words for token budget]"


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python debug/troubleshoot_empty_responses.py <assignment_id> [--model=MODEL] [--max_words=N] [--limit=N]")
        sys.exit(1)

    assignment_id = str(sys.argv[1])
    model = "gpt-4o-mini"
    max_words = 4000
    limit = None

    for arg in sys.argv[2:]:
        if arg.startswith("--model="):
            model = arg.split("=", 1)[1]
        elif arg.startswith("--max_words="):
            try:
                max_words = int(arg.split("=", 1)[1])
            except Exception:
                pass
        elif arg.startswith("--limit="):
            try:
                limit = int(arg.split("=", 1)[1])
            except Exception:
                pass

    debug_dir = os.path.join("data", "debug_outputs", f"{assignment_id}")
    ensure_dir(debug_dir)

    pdf_dir = os.path.join(FINAL_PDFS_DIR, assignment_id)
    pdf_paths = sorted(glob.glob(os.path.join(pdf_dir, "*.pdf")))
    if limit is not None:
        pdf_paths = pdf_paths[:limit]

    if not pdf_paths:
        print(f"No PDFs found at {pdf_dir}. Run a local grading prep first so final PDFs exist.")
        sys.exit(1)

    print(f"Analyzing {len(pdf_paths)} PDF(s) from {pdf_dir} using model '{model}' (max_words={max_words})\n")

    grader = OpenAIGrader(model=model)
    rubric = load_minimal_rubric()

    summary_rows = []

    for pdf_path in pdf_paths:
        user_id = os.path.splitext(os.path.basename(pdf_path))[0]
        print(f"\n📄 [{user_id}] Extracting text → {os.path.basename(pdf_path)}")

        text = extract_text_from_pdf(pdf_path)
        words = len(text.split()) if text else 0
        truncated_text = truncate_words(text, max_words=max_words)
        prompt_chars = len(truncated_text)

        result: Dict[str, Any] = {}
        status = "ok"
        reason = ""

        try:
            result = grader.grade(truncated_text, rubric)
            raw_feedback = (result or {}).get("overall_feedback", "").strip()
            if not result or not result.get("rubric_scores"):
                status = "empty_response"
                reason = raw_feedback or "Model returned no content"
        except Exception as e:
            status = "exception"
            reason = str(e)

        # Save artifacts
        artifact = {
            "user_id": user_id,
            "pdf_path": pdf_path,
            "words": words,
            "prompt_chars": prompt_chars,
            "model": model,
            "status": status,
            "reason": reason,
            "result": result,
        }
        with open(os.path.join(debug_dir, f"{user_id}_diagnostic.json"), "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2, ensure_ascii=False)

        summary_rows.append({
            "user_id": user_id,
            "words": words,
            "prompt_chars": prompt_chars,
            "status": status,
            "reason": reason,
        })

    # Write a human-friendly summary
    summary_path = os.path.join(debug_dir, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_rows, f, indent=2, ensure_ascii=False)

    # Also print a brief table to console
    print("\n\n==== Summary ====")
    failures = 0
    for row in summary_rows:
        tag = "✅" if row["status"] == "ok" else "❌"
        if row["status"] != "ok":
            failures += 1
        print(f"{tag} {row['user_id']}: {row['status']} | words={row['words']} | prompt_chars={row['prompt_chars']} | {row['reason']}")

    print(f"\nSaved per-file diagnostics in: {debug_dir}")
    print(f"Failures: {failures} / {len(summary_rows)}")


if __name__ == "__main__":
    main()


