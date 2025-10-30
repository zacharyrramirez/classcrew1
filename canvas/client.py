import os
from difflib import get_close_matches
from canvasapi import Canvas

class CanvasClient:
    def __init__(self):
        # These should come from your .env or environment
        self.api_url = os.getenv("CANVAS_API_URL")
        self.api_key = os.getenv("CANVAS_API_KEY")
        self.course_id = os.getenv("CANVAS_COURSE_ID")
        if not self.api_url or not self.api_key or not self.course_id:
            missing = []
            if not self.api_url: missing.append("CANVAS_API_URL")
            if not self.api_key: missing.append("CANVAS_API_KEY")
            if not self.course_id: missing.append("CANVAS_COURSE_ID")
            raise ValueError(f"Missing Canvas configuration: {', '.join(missing)}")

        try:
            numeric_course_id = int(str(self.course_id).strip())
        except Exception:
            raise ValueError(f"Invalid CANVAS_COURSE_ID: '{self.course_id}' (must be numeric)")
        
        try:
            self.canvas = Canvas(self.api_url, self.api_key)
            self.course = self.canvas.get_course(numeric_course_id)
        except Exception as e:
            error_msg = str(e)
            if "InvalidAccessToken" in error_msg or "401" in error_msg or "Unauthorized" in error_msg:
                raise ValueError(
                    f"Canvas API token is invalid or expired. Please:\n"
                    f"1. Go to Account Settings in the sidebar\n"
                    f"2. Generate a new Canvas API token (Canvas → Account → Settings → Approved Integrations → New Access Token)\n"
                    f"3. Update your token in Account Settings\n"
                    f"4. Verify your Canvas URL is correct: {self.api_url}"
                )
            elif "ResourceDoesNotExist" in error_msg or "404" in error_msg or "Not Found" in error_msg:
                raise ValueError(
                    f"Canvas course ID {numeric_course_id} not found. Please:\n"
                    f"1. Go to your Canvas course\n"
                    f"2. Copy the course ID from the URL (e.g., .../courses/12345)\n"
                    f"3. Update it in Account Settings"
                )
            else:
                raise ValueError(f"Canvas connection error: {error_msg}")

    def get_assignments(self, filter_by="all"):
        assignments = self.course.get_assignments()
        results = []
        for a in assignments:
            if filter_by == "all" or (filter_by == "published" and a.published):
                results.append({
                    "id": a.id,
                    "name": a.name,
                    "due_at": a.due_at,
                    "published": a.published
                })
        return results

    def get_rubric(self, assignment_id):
        assignment = self.course.get_assignment(int(assignment_id))
        if not hasattr(assignment, "rubric") or assignment.rubric is None:
            return []
        rubric_items = []
        for r in assignment.rubric:
            rubric_items.append({
                "criterion": r["description"],
                "max_points": float(r["points"]),
                "description": r.get("long_description", ""),
                "ratings": r.get("ratings", [])
            })
        return rubric_items

    def get_submissions(self, assignment_id, filter_by="submitted"):
        assignment = self.course.get_assignment(int(assignment_id))
        # Include 'user' to ensure all submission details, including attachments, are fetched.
        submissions = assignment.get_submissions(include=["user"])
        results = []
        for sub in submissions:
            sub_data = {
                "user_id": sub.user_id,
                "attempt": sub.attempt,
                "late": sub.late,
                "missing": sub.missing,
                "workflow_state": sub.workflow_state,
                "attachments": []
            }
            if hasattr(sub, "attachments") and sub.attachments:
                sub_data["attachments"] = sub.attachments
            results.append(sub_data)
        return results

    def download_submission_attachments(self, attachments, assignment_id, user_id, download_dir):
        """
        Downloads files from a submission's attachments list.
        This avoids re-fetching the submission object.
        """
        file_paths = []
        if attachments:
            for f in attachments:
                file_name = f.filename
                dest_path = os.path.join(download_dir, str(assignment_id), str(user_id))
                os.makedirs(dest_path, exist_ok=True)
                file_path = os.path.join(dest_path, file_name)
                if not os.path.exists(file_path):
                    try:
                        f.download(file_path)
                        print(f"✅ Downloaded: {file_path}")
                    except Exception as e:
                        print(f"❌ Error downloading file {file_name}: {e}")
                else:
                    print(f"♻️ File already exists: {file_path}")
                file_paths.append(file_path)
        return file_paths

    def post_score(self, assignment_id, user_id, grading_output):
        assignment = self.course.get_assignment(assignment_id)
        submission = assignment.get_submission(user_id)

        # Use the rubric_scores list of dicts (not string breakdowns)
        rubric_scores = grading_output.get("rubric_scores", [])
        score = sum([item.get("points", 0) for item in rubric_scores])
        feedback = grading_output.get("overall_feedback", "") or grading_output.get("feedback", "")

        print("\nCanvas rubric items (description → id):")
        rubric_id_map = {}
        for row in assignment.rubric:
            print(f"- '{row['description']}' → {row['id']}")
            rubric_id_map[row["description"]] = row["id"]

        # Build rubric_assessment mapping
        rubric_assessment = {}
        for item in rubric_scores:
            criterion_name = item["criterion"]
            canvas_id = rubric_id_map.get(criterion_name)
            if not canvas_id:
                matches = get_close_matches(criterion_name, rubric_id_map.keys(), n=1, cutoff=0.7)
                if matches:
                    matched_name = matches[0]
                    canvas_id = rubric_id_map[matched_name]
                    print(f"🔍 Matched '{criterion_name}' to Canvas rubric item '{matched_name}'")
                else:
                    print(f"⚠️ No Canvas rubric ID found for criterion: '{criterion_name}' (AI rubric)")
                    print(f"  Canvas rubric keys: {list(rubric_id_map.keys())}")
                    continue  # skip this criterion

            rubric_assessment[canvas_id] = {
                "points": item["points"],
                "comments": item.get("reason", "")
            }

        # Try posting rubric grade
        try:
            result = submission.edit(
                posted_grade=score,
                rubric_assessment=rubric_assessment,
                excuse=False
            )
            print("Canvas submission.edit() result:", result)
            print(f"✅ Posted rubric score {score} for user {user_id}")
        except Exception as e:
            print(f"❌ Error posting grade for user {user_id}: {e}")

        # Try posting feedback comment
        if feedback:
            try:
                result = submission.edit(comment={"text_comment": feedback})
                print(f"💬 Posted visible feedback comment for user {user_id}, result: {result}")
            except Exception as e:
                print(f"❌ Error posting feedback comment for user {user_id}: {e}")

    def upload_all_scores(self, assignment_id, results):
        for result in results:
            try:
                self.post_score(assignment_id, result["user_id"], result)
            except Exception as e:
                print(f"❌ Failed to upload score for user {result['user_id']}: {e}")
