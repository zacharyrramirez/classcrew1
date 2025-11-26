"""
grader.py
Implements an OpenAI-based grader that matches GraderBase interface.
"""

import json
import openai
import os
import base64
from io import BytesIO
from grader.base import GraderBase
from grader.prompts import OPENAI_SYSTEM_PROMPT, OPENAI_GRADER_INSTRUCTIONS

DEBUG_MODE = os.getenv("DEBUG_MODE") == "1"

class OpenAIGrader(GraderBase):
    def __init__(self, model="gpt-4o"):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.model = model

    def grade(self, submission_text, rubric_items, pdf_path=None):
        # Use vision if PDF provided, otherwise text-only
        if pdf_path and os.path.exists(pdf_path):
            try:
                return self._grade_with_vision(pdf_path, rubric_items)
            except Exception as e:
                print(f"⚠️ Vision grading failed ({e}), falling back to text-only")
                # Fallback to text if vision fails
        
        # Original text-only grading
        prompt = self._build_prompt(submission_text, rubric_items)
        
        # Debug: Check prompt length
        prompt_length = len(prompt)
        print(f"🔍 Debug - Prompt length: {prompt_length} characters")
        if prompt_length > 100000:  # Rough limit for most models
            print("⚠️ Warning - Prompt is very long, might cause issues")
        
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": OPENAI_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000
            )
            raw_text = response.choices[0].message.content
            if not raw_text:
                print("❌ OpenAI API returned an empty response.")
                print(f"🔍 Debug info - Model: {self.model}")
                print(f"🔍 Debug info - Response object: {response}")
                print(f"🔍 Debug info - Choices: {response.choices}")
                if hasattr(response.choices[0], 'finish_reason'):
                    print(f"🔍 Debug info - Finish reason: {response.choices[0].finish_reason}")
                return {
                    "rubric_scores": [],
                    "overall_feedback": "OpenAI returned an empty response."
                }
            
            raw_text = raw_text.strip()
            if DEBUG_MODE:
                print("🧪 OpenAI Raw Output:")
                print(raw_text)
            return self._extract_json(raw_text)
        except Exception as e:
            print(f"❌ OpenAI API error: {e}")
            return {
                "rubric_scores": [],
                "overall_feedback": f"OpenAI error: {e}"
            }

    def _build_prompt(self, submission_text, rubric_items):
        rubric_lines = []
        for item in rubric_items:
            line = f"- {item['criterion']} ({item['max_points']} pts): {item.get('description', 'No description')}"
            rubric_lines.append(line)
        rubric_block = "\n".join(rubric_lines)

        # Create a JSON template for the AI to fill out. This is more reliable.
        # Using json.dumps handles any special characters in the criterion names.
        json_template_items = []
        for item in rubric_items:
            template_item = {
                "criterion": item['criterion'],
                "points": f"<points for {item['criterion']}>",
                "reason": f"<reason for {item['criterion']}>"
            }
            json_template_items.append(json.dumps(template_item, indent=6))
        
        json_template = ",\n".join(json_template_items)

        return f"""{OPENAI_GRADER_INSTRUCTIONS}

### Rubric:
{rubric_block}

### Student Submission:
{submission_text}

Your task is to complete the following JSON object.
- Replace the placeholder values in angle brackets (e.g., "<points for...>") with your evaluation.
- Do NOT add or remove any criteria from the "rubric_scores" array.
- Provide a score and a detailed reason for every single criterion.
- Be fair and consistent - if in doubt, err on the side of giving students credit for their effort.

```json
{{
  "rubric_scores": [
{json_template}
  ],
  "overall_feedback": "<general summary of the submission quality and suggestions for improvement>"
}}
```
"""

    def _extract_json(self, text):
        try:
            if "```" in text:
                text = text.replace("```json", "").replace("```", "").strip()
            first_brace = text.find("{")
            last_brace = text.rfind("}")
            if first_brace != -1 and last_brace != -1:
                raw_json = text[first_brace:last_brace + 1]
                parsed = json.loads(raw_json)
                if self._validate_grading_json(parsed):
                    return parsed
                else:
                    print("❌ JSON schema validation failed.")
            else:
                print("❌ Could not find JSON brackets in OpenAI output.")
        except Exception as e:
            print("❌ JSON parsing error:", e)
        return {
            "rubric_scores": [],
            "overall_feedback": "OpenAI failed to return valid grading JSON."
        }

    def _validate_grading_json(self, data):
        if not isinstance(data, dict):
            return False
        if "rubric_scores" not in data or "overall_feedback" not in data:
            return False
        if not isinstance(data["rubric_scores"], list):
            return False
        for item in data["rubric_scores"]:
            if not isinstance(item, dict):
                return False
            if not all(k in item for k in ("criterion", "points", "reason")):
                return False
        if not isinstance(data["overall_feedback"], str):
            return False
        return True

    def _grade_with_vision(self, pdf_path, rubric_items):
        """Grade using GPT-4o with vision to see images, graphs, charts"""
        from pdf2image import convert_from_path
        from PIL import Image
        
        print(f"🖼️ Using vision mode for {os.path.basename(pdf_path)}")
        
        # Convert PDF to images (limit to 5 pages for cost control)
        images = convert_from_path(
            pdf_path,
            dpi=100,  # Lower DPI for cost efficiency
            first_page=1,
            last_page=5
        )
        
        # Build rubric text
        rubric_lines = []
        for item in rubric_items:
            line = f"- {item['criterion']} ({item['max_points']} pts): {item.get('description', 'No description')}"
            rubric_lines.append(line)
        rubric_block = "\n".join(rubric_lines)
        
        # Build JSON template
        json_template_items = []
        for item in rubric_items:
            template_item = {
                "criterion": item['criterion'],
                "points": f"<points for {item['criterion']}>",
                "reason": f"<reason for {item['criterion']}>"
            }
            json_template_items.append(json.dumps(template_item, indent=6))
        json_template = ",\n".join(json_template_items)
        
        # Build text prompt
        text_prompt = f"""{OPENAI_GRADER_INSTRUCTIONS}

### Rubric:
{rubric_block}

### Student Submission:
The submission is shown in the images below. Carefully review ALL images to evaluate the student's work.

Your task is to complete the following JSON object.
- Replace the placeholder values in angle brackets (e.g., "<points for...>") with your evaluation.
- Do NOT add or remove any criteria from the "rubric_scores" array.
- Provide a score and a detailed reason for every single criterion.
- Be fair and consistent - if in doubt, err on the side of giving students credit for their effort.

```json
{{
  "rubric_scores": [
{json_template}
  ],
  "overall_feedback": "<general summary of the submission quality and suggestions for improvement>"
}}
```
"""
        
        # Convert images to base64
        image_contents = []
        for i, img in enumerate(images):
            # Resize to max 768px width for cost efficiency
            img.thumbnail((768, 768), Image.Resampling.LANCZOS)
            
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            image_contents.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img_base64}",
                    "detail": "low"  # Use "low" detail mode for cost efficiency (85 tokens per image)
                }
            })
            print(f"  📄 Added page {i+1} to vision request")
        
        # Build message content with text + images
        content = [{"type": "text", "text": text_prompt}] + image_contents
        
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": OPENAI_SYSTEM_PROMPT},
                    {"role": "user", "content": content}
                ],
                max_tokens=1000
            )
            
            raw_text = response.choices[0].message.content
            if not raw_text:
                print("❌ OpenAI vision API returned empty response")
                return {
                    "rubric_scores": [],
                    "overall_feedback": "Vision grading returned empty response."
                }
            
            raw_text = raw_text.strip()
            if DEBUG_MODE:
                print("🧪 OpenAI Vision Raw Output:")
                print(raw_text)
            
            return self._extract_json(raw_text)
            
        except Exception as e:
            print(f"❌ OpenAI vision API error: {e}")
            raise  # Re-raise to trigger fallback in grade()
