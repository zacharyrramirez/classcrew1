pseudocode_thesis statement:

The AI Grader tool automatically pulls assignment submissions from Canvas and anonymizes each student by replacing their Canvas ID or name with an internal user ID (e.g., User 001). This ensures strict privacy for all subsequent grading steps.

For each assignment, the tool retrieves the matching rubric from Canvas, then uses OpenAI’s LLM to grade each rubric component. The resulting grade, feedback, and rubric are then passed to Gemini, which reviews the grading for fairness. If Gemini finds the grade fair, it approves it. If Gemini determines the grade is unfair, it will generate a revised grade and feedback, which replaces the original OpenAI result. This ensures that all students receive a fair and unbiased evaluation, leveraging both AI models for robust grading.

After all submissions are processed, the instructor reviews a holistic grading dashboard that displays anonymized student results, rubric comments, AI feedback, and provides access to the original (anonymized) submission—either via a file download or inline preview. This enables the instructor to verify whether each grade is fair or not. The instructor can edit any grades or comments before anything is returned to Canvas. A downloadable report is also available for bulk classes or offline review.

Only after instructor approval are grades and feedback pushed back to Canvas—accompanied by a clear disclosure to students that grading involved AI and was reviewed by a human. Upon successful submission, all local data, including anonymization keys, is securely deleted to protect privacy. The tool is designed to fail gracefully in the event of API or system issues, ensuring no data loss or privacy compromise at any stage.

Design details:
The grading dashboard presents, for each anonymized user:

-Anonymized ID (e.g., user001)

-Download or preview link for their submission (PDF, etc.)

-The AI-generated rubric breakdown and feedback

-Gemini review flag (“Fair”/“Unfair” with reason) and, if unfair, the Gemini-generated revised grade and feedback

-Editable fields for instructor override for points and comments

-Bulk download/report export option (CSV/Excel, with links to anonymized submissions)

Throughout the process, all files and displayed information remain anonymized—real identities are never shown to the instructor. This ensures that instructor review is robust, transparent, and privacy-first.


AI_GRADER_PROJECTV.2/
|
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── streamlit_app.py
|
├── canvas/
│   ├── __init__.py
│   ├── client.py
│   └── utils.py
|
├── data/
|
├── grader/
│   ├── __init__.py
│   ├── base.py
│   ├── grader.py
│   ├── reviewer.py
│   ├── rubric.py
│   └── workflows.py
|
├── utils/
│   ├── __init__.py
│   ├── anonymize.py
│   ├── cleanup.py
│   └── file_ops.py
|
├── .env
├── README.md
└── requirements.txt
