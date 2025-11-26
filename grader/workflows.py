from dotenv import load_dotenv 
import os
import csv

from grader.grader import OpenAIGrader
from grader.reviewer import AIFairnessChecker
from utils.anonymize import generate_anonymized_mapping
from utils.file_ops import prepare_submission_for_grading
from canvas.client import CanvasClient
from grader.rubric import validate_rubric, ensure_grading_completeness
from utils.config import FINAL_PDFS_DIR, GRADES_DIR, SUBMISSIONS_DIR

load_dotenv()

def grade_submissions(
    assignment_id,
    filter_by="submitted",
    stream_callback=None,
    override_map=None,
    external_submissions=None,
    status_filter=None,
    grade_missing_as_zero=False
):
    logs = []
    def log(msg):
        print(msg)
        logs.append(msg)
        if stream_callback:
            stream_callback(msg)

    assignment_id = str(assignment_id).strip()
    if not assignment_id.isdigit():
        log("❌ Invalid assignment ID. Must be a number.")
        raise ValueError("❌ Invalid assignment ID. Must be a number.")
    assignment_id = int(assignment_id)

    canvas = CanvasClient()
    rubric_items = canvas.get_rubric(assignment_id)
    if not rubric_items:
        log(f"❌ No rubric found on Canvas for assignment {assignment_id}")
        raise ValueError(f"❌ No rubric found on Canvas for assignment {assignment_id}")

    # Optional: Validate rubric structure
    try:
        validate_rubric(rubric_items)
    except Exception as e:
        log(f"❌ Invalid rubric: {e}")
        raise

    grader = OpenAIGrader()
    reviewer = AIFairnessChecker()

    submissions = external_submissions if external_submissions is not None else canvas.get_submissions(assignment_id, filter_by=filter_by)
    if status_filter:
        from utils.file_ops import get_submission_status
        submissions = [s for s in submissions if get_submission_status(s) in status_filter]

    real_ids = [str(s["user_id"]) for s in submissions]
    anon_map = generate_anonymized_mapping(real_ids)

    all_results = []
    extraction_failures = []

    total = len(submissions)
    if stream_callback and hasattr(stream_callback, "update_progress") and callable(stream_callback.update_progress):
        stream_callback.update_progress(0, total)

    os.makedirs(FINAL_PDFS_DIR, exist_ok=True)

    for i, sub in enumerate(submissions):
        if grade_missing_as_zero and sub.get("missing"):
            user_id = sub["user_id"]
            anon_id = anon_map.get(str(user_id), f"user???")
            log(f"❌ No submission for {anon_id}. Assigning zero.")
            all_results.append({
                "user_id": user_id,
                "anon_id": anon_id,
                "score": 0,
                "was_regraded": False,
                "review_reason": "Missing submission",
                "feedback": "No submission received.",
                "rubric_details": "No work submitted.",
                "rubric_scores": [
                    {
                        "criterion": item["criterion"],
                        "points": 0,
                        "reason": "No work submitted."
                    } for item in rubric_items
                ],
                "submission_status": "Missing",
                "original_score": "",
                "original_feedback": ""
            })
            if stream_callback and hasattr(stream_callback, "update_progress") and callable(stream_callback.update_progress):
                stream_callback.update_progress(i + 1, total)
            continue

        user_id = sub["user_id"]
        anon_id = anon_map.get(str(user_id), f"user???")

        # Assign readable status
        status = "On Time"
        if sub.get("missing"):
            status = "Missing"
        elif sub.get("late"):
            status = "Late"
        elif sub.get("attempt") is None:
            status = "Missing"
        elif sub.get("attempt", 1) > 1:
            status = "Resubmitted"

        try:
            attachments = sub.get("attachments", [])
            if not attachments:
                log(f"⚠️ No submission files (attachments) found for {anon_id}. Skipping.")
                continue

            log(f"📥 Found {len(attachments)} file(s) for {anon_id}.")
            file_paths = canvas.download_submission_attachments(attachments, assignment_id, user_id, SUBMISSIONS_DIR)

            if not file_paths:
                log(f"⚠️ Downloading failed for all files for {anon_id}. Skipping.")
                continue

            # Always output the final PDF to FINAL_PDFS_DIR/<assignment_id>/<user_id>.pdf
            final_pdf_dir = os.path.join(FINAL_PDFS_DIR, str(assignment_id))
            os.makedirs(final_pdf_dir, exist_ok=True)
            output_path = os.path.join(final_pdf_dir, f"{user_id}.pdf")
            log(f"📎 Creating final PDF at: {output_path}")
            merged_path, content_text = prepare_submission_for_grading(file_paths, output_path)
            log(f"📄 Extracted {len(content_text.split())} words of text from final PDF.")

            if not content_text.strip():
                msg = f"⚠️ No extractable text in submission for {anon_id}. Skipping."
                log(msg)
                extraction_failures.append({
                    "user_id": user_id,
                    "anon_id": anon_id,
                    "status": status,
                    "reason": "No extractable text in submission"
                })
                continue

            grading_result = grader.grade(content_text, rubric_items, pdf_path=merged_path)
            grading_result = ensure_grading_completeness(grading_result, rubric_items)
            # Convert all points to integers to avoid type errors
            for item in grading_result.get("rubric_scores", []):
                if "points" in item:
                    item["points"] = int(float(item["points"]))
            log(f"🤖 Grading complete for {anon_id}. Running fairness review...")
            fair, reason, revised_grade, confidence = reviewer.review(grading_result, rubric_items, merged_path)  # type: ignore
            if fair:
                log(f"🧠 Gemini review passed: grade considered fair for {anon_id}.")
            else:
                log(f"⚠️ Gemini flagged {anon_id} as unfair (confidence: {confidence:.2f}): {reason}")

            # Save original AI score/feedback in case of Gemini regrade
            was_regraded = False
            original_score = sum(item["points"] for item in grading_result.get("rubric_scores", []))
            original_feedback = grading_result.get("overall_feedback", "").strip()

            # Only apply revision if confidence is high enough (0.7 or higher)
            if not fair and revised_grade and confidence >= 0.7:
                # Also ensure the revised grade is complete
                revised_grade = ensure_grading_completeness(revised_grade, rubric_items)
                # Convert all points to integers to avoid type errors
                for item in revised_grade.get("rubric_scores", []):
                    if "points" in item:
                        item["points"] = int(float(item["points"]))
                revised_score = sum(item["points"] for item in revised_grade.get("rubric_scores", []))
                log(f"♻️ Gemini revised grade for {anon_id} from {original_score} to {revised_score} points (confidence: {confidence:.2f}).")
                grading_result['original_score'] = original_score
                grading_result['original_feedback'] = original_feedback
                grading_result = revised_grade
                was_regraded = True
            elif not fair and confidence < 0.7:
                log(f"⚠️ Gemini flagged {anon_id} as potentially unfair but confidence too low ({confidence:.2f}) - keeping original grade.")
            else:
                log(f"✅ Graded {anon_id} for {original_score} points. Feedback created.")

            rubric_scores = [
                {
                    **item,
                    "points": int(float(item["points"])) if int(float(item["points"])) >= int(float(item.get("max_points", item["points"]))) else 0
                }
                for item in grading_result.get("rubric_scores", [])
            ]
            total_score = sum(item["points"] for item in rubric_scores)
            general_comment = grading_result.get("overall_feedback", "").strip()

            # Append AI grading note to the general comment
            if general_comment:
                general_comment += "\n\nThis was graded by AI and submitted after human review."
            else:
                general_comment = "This was graded by AI and submitted after human review."

            # --- Handle manual overrides ---
            if override_map and user_id in override_map:
                log(f"✏️ Manual override applied for {anon_id} by instructor.")
                override = override_map[user_id]
                total_score = override["score"]
                general_comment = override["feedback"]
                rubric_scores = override.get("rubric_scores", [
                    {
                        "criterion": "Manual Override",
                        "points": total_score,
                        "reason": "Instructor override"
                    }
                ])
                was_regraded = True
                
            rubric_lines = [
                f"{item['criterion']}: {item['points']} — {item['reason']}"
                for item in rubric_scores
            ]
            rubric_feedback = "\n".join(rubric_lines)

            all_results.append({
                "user_id": user_id,
                "anon_id": anon_id,
                "score": total_score,
                "was_regraded": was_regraded,
                "review_reason": reason if not fair else "",
                "feedback": general_comment,
                "rubric_details": rubric_feedback,
                "rubric_scores": rubric_scores,  # <-- This is new and needed!
                "submission_status": status,
                "original_score": original_score if was_regraded else "",
                "original_feedback": original_feedback if was_regraded else ""
            })

            grading_result["rubric_scores"] = rubric_scores
            grading_result["overall_feedback"] = general_comment
            
            if stream_callback and hasattr(stream_callback, "update_progress") and callable(stream_callback.update_progress):
                stream_callback.update_progress(i + 1, total)

        except Exception as e:
            log(f"❌ Error grading user {anon_id}: {e}")
            extraction_failures.append({
                "user_id": user_id,
                "anon_id": anon_id,
                "status": status,
                "reason": str(e)
            })

    # --- Export CSV ---
    csv_path = None
    if all_results:
        os.makedirs(GRADES_DIR, exist_ok=True)
        csv_path = os.path.join(GRADES_DIR, f"{assignment_id}_grades.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_results[0].keys())
            writer.writeheader()
            writer.writerows(all_results)
        log(f"📁 Exported grades to {csv_path}")
    else:
        log("⚠️ No results to export.")

    # --- Cleanup Temporary Files ---
    # Do NOT clean up files here. Cleanup should be done after grades are posted to Canvas.
    log("✅ Batch grading complete. (Files will be cleaned up after grades are posted.)")

    return {
        "results": all_results,
        "rubric": rubric_items,
        "assignment_id": assignment_id,
        "csv_path": csv_path if all_results else None,
        "logs": logs,
        "extraction_failures": extraction_failures
    }
