# AI Grader Project v2

**Automated, privacy-first grading and feedback for Canvas LMS assignments using OpenAI Vision and Gemini.**

---

## 🚀 Overview

AI Grader is an automated, privacy-focused grading tool for educators using Canvas LMS. It:
- **Anonymizes all students** from the start—no real names/IDs ever reach the grading or instructor review stages.
- **Grades each submission using OpenAI's LLM** against the official Canvas rubric.
- **Double-checks grading fairness** with Gemini, replacing the grade if unfairness is detected.
- **Gives instructors the final say**—all grades/feedback are editable and reviewed in an easy dashboard before returning anything to Canvas.
- **Cleans up all data** after grading, ensuring strict privacy and compliance.

---

## 🧭 Workflow (How It Works)

1. **Fetch Assignments**: Pulls submissions and rubric from Canvas for the chosen assignment.
2. **Anonymize**: Replaces student names/IDs with internal labels (`user001`, `user002`, ...).
3. **AI Grading**: OpenAI grades each submission per rubric component.
4. **Fairness Review**: Gemini reviews the grade. If flagged "unfair," it generates a new grade/feedback.
5. **Instructor Dashboard**:
    - View anonymized results, rubric breakdown, and feedback.
    - Download or preview original (anonymized) submissions.
    - Edit any grade/comment before approval.
    - Flag/review students skipped due to file issues.
    - Export anonymized reports for records or offline review.
6. **Final Approval & Upload**: Instructor approves and uploads grades/feedback to Canvas (with an AI grading disclosure).
7. **Cleanup**: All local files, mapping keys, and temporary data are securely deleted.

---

## 📁 Project Structure

ai_grader_v.2/
│
├── app/
│   ├── __init__.py
│   ├── streamlit_app.py       # Streamlit UI (dashboard entry point)
│   ├── ui_assignment.py       # Assignment selection and rubric preview UI
│   └── ui_grading.py          # Grading/review UI
│
├── canvas/
│   ├── __init__.py
│   ├── client.py              # Canvas API integration
│   └── utils.py               # Canvas helpers (status parsing)
│
├── grader/
│   ├── __init__.py
│   ├── base.py                # Grader/reviewer base classes
│   ├── grader.py              # OpenAI LLM grading logic
│   ├── reviewer.py            # Gemini fairness check logic
│   ├── rubric.py              # Rubric validation/formatting
│   └── workflows.py           # Pipeline engine (end-to-end flow)
│
├── utils/
│   ├── __init__.py
│   ├── anonymize.py           # Anonymization mapping (IDs)
│   ├── cleanup.py             # Secure file/data cleanup
│   ├── config.py              # Directory and config constants
│   └── file_ops.py            # File merging, extraction, conversion
│
├── data/                      # Temporary files (auto-created/cleaned)
│   ├── grades/
│   ├── submissions/
│   ├── final_pdfs/
│   ├── debug_outputs/
│   └── merged_pdfs/
│
├── main.py                    # CLI entry point for batch grading
├── requirements.txt           # Python dependencies
├── README_ai_grader_v2.md     # This file
└── pseudocode_thesis.md       # (Design notes)

---

## ⚡️ Quick Start

1. **Clone the repo** and install requirements:
   ```bash
   git clone <your_repo_url>
   cd ai_grader_v.2
   pip install -r requirements.txt
   ```
2. **Set up `.env`:**  
   Add your API keys and Canvas info:
   ```
   OPENAI_API_KEY=your-openai-key
   GEMINI_API_KEY=your-gemini-key
   CANVAS_API_KEY=your-canvas-token
   CANVAS_API_URL=https://your-institution.instructure.com
   CANVAS_COURSE_ID=123456
   ```

3. **Run the Streamlit dashboard:**
   ```bash
   streamlit run app/streamlit_app.py
   ```
   Or use the CLI for batch grading:
   ```bash
   python main.py <assignment_id> [--post] [--filter=submitted|late|both]
   ```
   - `--post` will actually post grades to Canvas (with confirmation).
   - `--filter` lets you select which submissions to grade (default: submitted).

---

## 💡 Features & Design Highlights

- **Total Anonymization:** No real names or IDs ever reach the AI or the instructor.
- **Multi-model Grading:** Uses both OpenAI and Gemini for robust, fair, and unbiased grading.
- **Instructor-First:** Human review, edit, and approval before anything goes to Canvas.
- **Automated Cleanup:** All temp files and mapping keys securely deleted after grading.
- **Graceful Fallbacks:** Handles unsupported files, missing submissions, and API errors without data loss.

---

## 🔒 Privacy & Security

- All student data is anonymized before grading.
- Temporary files are deleted after grades are uploaded.
- No mapping between anonymized IDs and real students is retained.
- Instructors only see anonymized labels in the dashboard.

---

## 📝 FAQ

**Q: What if a student submits a file that isn't a PDF or DOCX?**  
A: Those files are skipped. The student will be flagged as "submission not graded—unsupported file type." You can notify the student to resubmit as PDF/DOCX.

**Q: What happens if there's a grading or API error?**  
A: The tool fails gracefully, logs the issue, and flags any affected students for manual review.

**Q: Can I edit grades or feedback before they're posted?**  
A: Yes! All results are editable in the dashboard before uploading to Canvas.

**Q: Are rubrics required?**  
A: Yes—every assignment must have a Canvas rubric attached, or grading will not proceed.

---

## 🧑‍💻 Who Should Use This?

- Instructors using Canvas LMS who want fast, privacy-first, high-quality AI grading.
- Not recommended for assignments without clear rubrics or where subjective, non-text submissions (like artwork) dominate.

---

## 🤝 Support & Contributions

- For issues or feature requests, open an issue or pull request.
- For private deployments or consulting, contact [zacharyrramirez@gmail.com].

---
