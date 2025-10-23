# reviewer.py
import os
import json
import google.generativeai as genai  # type: ignore
from grader.base import ReviewerBase
from grader.prompts import GEMINI_REVIEWER_INSTRUCTIONS, GEMINI_SYSTEM_PROMPT

DEBUG_MODE = os.getenv("DEBUG_MODE") == "1"

def format_rubric_for_prompt(rubric_items):
    sections = []
    for item in rubric_items:
        block = f"- {item['criterion']} ({item['max_points']} pts): {item['description'] or 'No description provided.'}"
        if item.get("ratings"):
            for rating in item["ratings"]:
                blurb = rating.get("long_description", "").strip()
                block += f"\n  • {rating['description']} ({rating['points']} pts): {blurb or 'No explanation provided.'}"
        sections.append(block)
    return "\n\n".join(sections)

def build_json_template(rubric_items):
    """Builds a JSON string template for the AI to fill out."""
    json_template_items = []
    for item in rubric_items:
        template_item = {
            "criterion": item['criterion'],
            "points": f"<points for {item['criterion']}>",
            "reason": f"<reason for {item['criterion']}>"
        }
        json_template_items.append(json.dumps(template_item, indent=8))
    
    template_str = ",\n".join(json_template_items)
    return f"""{{
      "rubric_scores": [
{template_str}
      ],
      "overall_feedback": "<general summary of the submission quality and suggestions>"
    }}"""

def extract_review_json(text):
    try:
        if "```" in text:
            text = text.replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            raw_json = text[start:end+1]
            data = json.loads(raw_json)
            fair = data.get("fair", True)
            reason = data.get("reason", "") if not fair else ""
            revised_grade = data.get("suggested_grading_result") if not fair else None
            confidence = data.get("confidence", 0.5)
            return fair, reason, revised_grade, confidence
    except Exception as e:
        print(f"❌ Reviewer JSON parse error: {e}")
    # Default return for all error cases - low confidence
    return True, "Gemini returned unreadable review response.", None, 0.0

class AIFairnessChecker(ReviewerBase):
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))  # type: ignore
        self.model = genai.GenerativeModel("gemini-2.5-flash-lite")  # type: ignore

    def review(self, grading_result, rubric_items, submission_path):
        if not submission_path or not os.path.exists(submission_path):
            raise FileNotFoundError("❌ Submission file is required for fairness review but was not found.")

        uploaded_file = None
        try:
            # 1. Upload the file to the Files API
            print(f"🧠 Uploading {os.path.basename(submission_path)} for fairness review...")
            uploaded_file = genai.upload_file(path=submission_path, display_name=os.path.basename(submission_path))  # type: ignore
            print(f"✅ File uploaded successfully: {uploaded_file.name}")

            rubric_prompt = format_rubric_for_prompt(rubric_items)
            json_template = build_json_template(rubric_items)
            
            # Dynamically create the final prompt section
            response_format_prompt = f"""
Your response MUST be a single JSON object with the following structure.
If the original grade is FAIR, the `suggested_grading_result` MUST be null.
If the original grade is UNFAIR, you MUST provide a `suggested_grading_result`.

```json
{{
  "fair": <true or false>,
  "reason": "<If unfair, explain the key error in the original grade. If fair, this should be an empty string.>",
  "confidence": <0.0 to 1.0, indicating your certainty about this assessment>,
  "suggested_grading_result": null | {json_template}
}}
```
"""
            prompt = f"""{GEMINI_SYSTEM_PROMPT}

{GEMINI_REVIEWER_INSTRUCTIONS}

Rubric:
{rubric_prompt}

Original Grade to Review:
```json
{json.dumps(grading_result, indent=2)}
```

{response_format_prompt}
"""
            # 2. Make the request using the uploaded file
            response = self.model.generate_content([prompt, uploaded_file])
            text = response.text.strip()

            if DEBUG_MODE:
                os.makedirs("debug_outputs", exist_ok=True)
                debug_path = f"debug_outputs/{os.path.basename(submission_path)}_fairness_review.txt"
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"🧠 Saved reviewer response to: {debug_path}")

            return extract_review_json(text)

        except Exception as e:
            print(f"❌ Gemini Reviewer Exception: {e}")
            return True, f"Error running Gemini review: {e}", None, 0.5
        finally:
            # 3. Clean up the uploaded file
            if uploaded_file:
                print(f"🧹 Deleting temporary uploaded file: {uploaded_file.name}")
                genai.delete_file(uploaded_file.name)  # type: ignore
