from grader.workflows import grade_submissions
import sys
import os
from utils.config import MERGED_PDFS_DIR, GRADES_DIR, SUBMISSIONS_DIR, DEBUG_DIR

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <assignment_id> [--post] [--filter=submitted|late|both]")
        print("  --post     Actually post grades to Canvas (requires confirmation).")
        print("  --filter=  Submission filter: submitted (default), late, both.")
        sys.exit(1)

    assignment_id = sys.argv[1]
    post_grades = "--post" in sys.argv
    filter_by = "submitted"

    for arg in sys.argv[2:]:
        if arg.startswith("--filter="):
            filter_by = arg.split("=", 1)[1]

    # Run grading
    results = grade_submissions(
        assignment_id=assignment_id,
        filter_by=filter_by,
        stream_callback=print,
        override_map=None,  # No manual overrides via CLI
    )

    # Write CSV of results for audit
    csv_path = results.get("csv_path")
    if csv_path and os.path.exists(csv_path):
        print(f"[INFO] Exported grades to {csv_path}")

    # Only post grades if --post is present
    if post_grades:
        confirm = input("Are you SURE you want to post grades to Canvas? [y/N]: ").lower()
        if confirm == "y":
            grade_submissions(
                assignment_id=assignment_id,
                filter_by=filter_by,
                override_map=None,
                stream_callback=print
            )
            print("✅ Grades posted to Canvas.")
            # Cleanup temp files after posting
            from utils.cleanup import cleanup_multiple
            cleanup_dirs = [MERGED_PDFS_DIR, GRADES_DIR, SUBMISSIONS_DIR, DEBUG_DIR]
            cleanup_multiple(cleanup_dirs)
            print("🧹 All temporary files securely deleted.")
        else:
            print("❌ Posting cancelled. No grades were sent to Canvas.")
    else:
        print("[DRY RUN] No grades posted. Run with --post to actually post grades.")

if __name__ == "__main__":
    main()
