"""
rubric.py

Helpers for parsing, validating, and formatting grading rubrics for AI-based graders/reviewers.
"""

def validate_rubric(rubric_items):
    for i, item in enumerate(rubric_items):
        try:
            mp = float(item["max_points"])
            if mp < 1:
                print(f"WARNING: Rubric item {i} has <1 max_points: {item}")
        except Exception as e:
            print(f"ERROR: Rubric item {i} has non-numeric max_points: {item}, error: {e}")
    return True


def format_rubric_for_prompt(rubric_items):
    """
    Returns a plain-text string for use in LLM grading/review prompts.
    """
    sections = []
    for item in rubric_items:
        line = f"- {item['criterion']} ({item['max_points']} pts): {item['description'] or 'No description'}"
        if item.get("ratings"):
            for rating in item["ratings"]:
                blurb = rating.get("long_description", "").strip()
                line += f"\n  • {rating['description']} ({rating['points']} pts): {blurb or 'No explanation provided.'}"
        sections.append(line)
    return "\n\n".join(sections)

def rubric_total_points(rubric_items):
    """
    Returns the total maximum score possible for a rubric.
    """
    return sum(item.get("max_points", 0) for item in rubric_items)

def get_criterion_names(rubric_items):
    """
    Returns a list of criterion names in order.
    """
    return [item["criterion"] for item in rubric_items]

def ensure_grading_completeness(grading_result, rubric_items):
    """
    Ensures the grading result has a score for every rubric criterion.
    If a criterion is missing from the AI's output, this function adds a
    default entry with 0 points and a standard reason.
    """
    if not grading_result or "rubric_scores" not in grading_result:
        return grading_result 

    graded_criteria = {score['criterion'] for score in grading_result['rubric_scores']}

    for item in rubric_items:
        if item['criterion'] not in graded_criteria:
            grading_result['rubric_scores'].append({
                "criterion": item['criterion'],
                "points": 0,
                "reason": "This criterion was not addressed in the submission."
            })
    return grading_result
