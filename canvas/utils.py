"""
utils.py

Helper functions for Canvas API data normalization and workflow utilities.
These helpers are used throughout the pipeline to standardize Canvas data
for grading, review, and dashboard display.
"""

from datetime import datetime

def parse_canvas_datetime(dt_str):
    """
    Converts a Canvas ISO8601 datetime string to a Python datetime object.
    Returns None if parsing fails.
    """
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except Exception:
        return None

def get_submission_status(sub):
    """
    Maps a Canvas submission dict to a standard status string:
    "On Time", "Late", "Missing", or "Resubmitted".
    """
    if sub.get("attempt") is None or sub.get("missing"):
        return "Missing"
    elif sub.get("late"):
        return "Late"
    elif sub.get("attempt", 1) > 1:
        return "Resubmitted"
    else:
        return "On Time"

def extract_filenames(submission_files):
    """
    Given a list of file dicts from Canvas, returns a list of filenames.
    """
    return [f["filename"] for f in submission_files if "filename" in f]

def safe_get(dct, *keys, default=None):
    """
    Safely traverse nested dict keys.
    Example: safe_get(submission, "user", "name", default="Unknown")
    """
    for k in keys:
        if isinstance(dct, dict) and k in dct:
            dct = dct[k]
        else:
            return default
    return dct

def filter_submissions_by_status(submissions, status):
    """
    Given a list of Canvas submission dicts and a status ("On Time", "Late", "Missing", "Resubmitted"),
    returns only those submissions matching the status.
    """
    return [s for s in submissions if get_submission_status(s) == status]

def all_submission_statuses(submissions):
    """
    Returns a dict counting each submission status in the list of submissions.
    Useful for dashboard summaries.
    Example return: { "On Time": 17, "Late": 3, "Missing": 2 }
    """
    from collections import Counter
    return dict(Counter(get_submission_status(s) for s in submissions))
