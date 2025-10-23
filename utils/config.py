import os
import tempfile

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Use persistent volume for data in production, temp directory for local development
if os.path.exists("/app/data"):
    # Production environment (Fly.io with mounted volume)
    DATA_ROOT = "/app/data"
else:
    # Local development
    DATA_ROOT = os.path.join(PROJECT_ROOT, "data")

FINAL_PDFS_DIR = os.path.join(DATA_ROOT, "final_pdfs")
MERGED_PDFS_DIR = os.path.join(DATA_ROOT, "merged_pdfs")
SUBMISSIONS_DIR = os.path.join(DATA_ROOT, "submissions")
GRADES_DIR = os.path.join(DATA_ROOT, "grades")
DEBUG_DIR = os.path.join(DATA_ROOT, "debug_outputs")

# Ensure directories exist
for directory in [FINAL_PDFS_DIR, MERGED_PDFS_DIR, SUBMISSIONS_DIR, GRADES_DIR, DEBUG_DIR]:
    os.makedirs(directory, exist_ok=True)