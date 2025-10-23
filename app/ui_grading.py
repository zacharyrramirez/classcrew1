# app/ui_grading.py

import os
import pandas as pd
import streamlit as st
from grader.workflows import grade_submissions
from utils.config import FINAL_PDFS_DIR
from utils.file_ops import get_submission_status
from canvas.client import CanvasClient  # <- Moved up to avoid import cycles
from utils.cleanup import cleanup_assignment_files

def render_grading_section(assignment_id, rubric_items, assignment_options=None, submission_filter=None, filtered_submissions=None):
    st.header("2️⃣ Filter and Run AI Grading")
    status_filter = st.multiselect(
        "📂 Filter which submissions to grade:",
        options=["On Time", "Late", "Missing", "Resubmitted"],
        default=["On Time", "Late", "Resubmitted"]
    )

    canvas = None
    selected_subs = []

    # The UI will now only stream messages, not collect them.
    # The workflow function is the single source of truth for logs.
    def stream_to_ui(msg):
        st.write(msg)

    grade_missing_as_zero = st.checkbox("🟥 Assign a score of 0 to Missing submissions")
    results_payload = None  # <-- To store the whole dict returned by the workflow

    # Remove redundant rubric loading - we'll use the one from grading results
    # rubric_items = CanvasClient().get_rubric(assignment_id)
    # max_score = sum(item['max_points'] for item in rubric_items) if rubric_items else 50  # fallback to 50

    # The test button has been removed to restore the standard workflow.
    # if st.button("🧪 Test Preview with Saved Grades"):
    # ... (code for testing)

    if st.button("🚀 Run AI Grading"):
        if filtered_submissions is not None:
            submissions = filtered_submissions
        else:
            canvas = CanvasClient()
            submissions = canvas.get_submissions(assignment_id)
        with st.spinner("Grading in progress..."):
            for sub in submissions:
                status = get_submission_status(sub)
                # Include missing submissions if grade_missing_as_zero is checked, regardless of status filter
                if status in status_filter or (grade_missing_as_zero and status == "Missing"):
                    sub["grading_status"] = status
                    selected_subs.append(sub)

            if not selected_subs:
                st.warning("⚠️ No submissions matched the selected filters.")
            else:
                # The `logs` parameter is removed from the call.
                # The full results dictionary is captured.
                results_payload = grade_submissions(
                    grade_missing_as_zero=grade_missing_as_zero,
                    assignment_id=assignment_id,
                    filter_by="submitted",
                    stream_callback=stream_to_ui,
                    external_submissions=selected_subs
                )
                st.success("✅ Grading complete!")
                # The results and logs are extracted from the returned payload
                st.session_state["grading_results"] = results_payload
                st.session_state["grading_logs"] = results_payload.get("logs", [])
                st.session_state["overrides"] = {}

    # DISPLAY GRADING PREVIEW AND POSTING SECTION (only after grading)
    if "grading_results" in st.session_state:
        results = st.session_state["grading_results"]
        rubric_items = results["rubric"]
        max_score = sum(item['max_points'] for item in rubric_items) if rubric_items else 50
        st.sidebar.markdown("## 📝 Rubric Reference")
        for item in rubric_items:
            st.sidebar.markdown(f"**{item['criterion']}**: (Max: {int(item['max_points'])})")
            if item.get("description"):
                st.sidebar.markdown(f":small_blue_diamond: _{item['description']}_")
            if item.get("ratings"):
                for rating in item["ratings"]:
                    st.sidebar.markdown(
                        f"- **{rating['description']}** ({rating['points']} pts): {rating.get('long_description', '')}"
                    )
            st.sidebar.markdown("---")

        st.markdown("## 📊 Grade Preview")
        if "edited_results" not in st.session_state:
            # Deep copy to allow edits
            import copy
            st.session_state["edited_results"] = copy.deepcopy(results["results"])
            st.session_state["original_results"] = copy.deepcopy(results["results"])

        edited_results = st.session_state["edited_results"]
        original_results = st.session_state["original_results"]

        for i, result in enumerate(edited_results):
            with st.expander(f"{result['anon_id']} — {result['score']} pts ({result['submission_status']})", expanded=False):
                # 1. Display total score as int (no decimals)
                st.markdown(f"### 🧾 Total Score: **{int(result['score'])} / {int(max_score)}**")
                if result.get("review_reason"):
                    st.warning(f"⚠️ Gemini regrade reason: {result.get('review_reason')}")

                st.markdown("#### 📚 Rubric Breakdown")
                rubric_feedback = result.get("rubric_scores", [])
                total_score = 0
                
                # Loop through the official Canvas rubric to maintain order
                for item in rubric_items:
                    criterion = item["criterion"]
                    max_points = item["max_points"]
                    
                    # Find the corresponding score and comment from the graded results
                    # This is more robust than using a dictionary lookup
                    # We strip whitespace to handle potential inconsistencies between Canvas and AI output
                    graded_item = next((r for r in rubric_feedback if r.get("criterion", "").strip() == criterion.strip()), None)
                    
                    awarded = graded_item.get("points", 0) if graded_item else 0
                    comment = graded_item.get("reason", "") if graded_item else "Comment not found."

                    col1, col2 = st.columns([1, 4])
                    with col1:
                        new_awarded = st.number_input(
                            f"{criterion} ({int(max_points)} pts)", 
                            min_value=0, 
                            max_value=int(max_points), 
                            value=int(awarded), 
                            step=1,
                            key=f"{criterion}_pts_{result['anon_id']}"
                        )
                    with col2:
                        new_comment = st.text_area(
                            f"Feedback for {criterion}", value=comment, key=f"{criterion}_comment_{result['anon_id']}", placeholder="No comment provided")
                    # Update rubric_scores in session_state
                    if graded_item:
                        graded_item["points"] = new_awarded
                        graded_item["reason"] = new_comment
                    
                    total_score += new_awarded
                # Update total score
                result["score"] = total_score

                st.markdown("#### 📝 General Feedback")
                new_feedback = st.text_area("Overall Comment", value=result["feedback"], key=f"comment_{i}")
                result["feedback"] = new_feedback

                st.markdown("#### 📄 Submission Preview")
                # (3) Improved preview logic
                # Always look for the final PDF in FINAL_PDFS_DIR/<assignment_id>/<user_id>.pdf
                final_pdf_path = os.path.join(FINAL_PDFS_DIR, str(result.get('assignment_id', assignment_id)), f"{result['user_id']}.pdf")
                found_file = False
                # Detect debug/preview mode ONLY by checking if assignment_id is 'debug'
                debug_mode = str(results.get("assignment_id", "")).lower() == "debug"
                if debug_mode:
                    st.info("No submission file found. (This is expected in preview/debug mode.)")
                    found_file = True
                elif os.path.exists(final_pdf_path):
                    with open(final_pdf_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Download Submission (Final PDF)",
                            data=f.read(),
                            file_name=f"{result['anon_id']}.pdf",
                            mime="application/pdf",
                            key=f"download_{i}"
                        )
                    # The iframe is unreliable for local files, so it has been removed.
                    # components.iframe(f"file://{os.path.abspath(final_pdf_path)}", height=600)
                    found_file = True
                if not found_file:
                    st.info("No final submission PDF found for this student.")

                # Undo button
                if st.button(f"Undo changes for {result['anon_id']}", key=f"undo_{i}"):
                    # Restore from original
                    edited_results[i] = copy.deepcopy(original_results[i])
                    st.rerun()

        # Export to CSV
        if st.button("⬇️ Export Current Grades to CSV"):
            df_export = pd.DataFrame(edited_results)
            csv = df_export.to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV", csv, file_name="edited_grades.csv")

        # Final review/confirmation
        if st.button("Review All Changes Before Submission"):
            st.session_state["show_review_modal"] = True

        if st.session_state.get("show_review_modal", False):
            st.markdown("### 📝 Review All Changes")
            st.info("Below is a summary of all changes made. Please confirm before submitting to Canvas.")

            def render_text_diff(label, from_text, to_text, key_prefix):
                """Helper to render a prettier side-by-side text diff."""
                st.markdown(f"**{label}**")
                col1, col2 = st.columns(2)
                with col1:
                    st.caption("From")
                    st.markdown(f"<div style='background-color:rgba(255, 75, 75, 0.1); border: 1px solid rgba(255, 75, 75, 0.2); border-radius:5px; padding:10px; height: 150px; overflow-y: auto;'>{from_text}</div>", unsafe_allow_html=True)
                with col2:
                    st.caption("To")
                    st.markdown(f"<div style='background-color:rgba(75, 255, 75, 0.1); border: 1px solid rgba(75, 255, 75, 0.2); border-radius:5px; padding:10px; height: 150px; overflow-y: auto;'>{to_text}</div>", unsafe_allow_html=True)

            any_changes = False
            for i, (orig, edit) in enumerate(zip(original_results, edited_results)):
                if orig != edit:
                    any_changes = True
                    with st.container():
                        st.markdown("---")
                        st.markdown(f"### Student: **{edit['anon_id']}**")

                        # 1. Score change
                        orig_score = orig.get('score', 0)
                        edit_score = edit.get('score', 0)
                        if orig_score != edit_score:
                            st.metric(label="Total Score", value=f"{edit_score} pts", delta=f"{edit_score - orig_score:+.0f} pts")

                        # 2. Overall Feedback change
                        orig_feedback = orig.get('feedback', '')
                        edit_feedback = edit.get('feedback', '')
                        if orig_feedback != edit_feedback:
                            render_text_diff("Overall Feedback", orig_feedback, edit_feedback, f"feedback_{i}")

                        # 3. Rubric Score changes
                        orig_rubric = {item.get('criterion', '').strip(): item for item in orig.get('rubric_scores', [])}
                        edit_rubric = {item.get('criterion', '').strip(): item for item in edit.get('rubric_scores', [])}
                        all_criteria = sorted(list(set(orig_rubric.keys()) | set(edit_rubric.keys())))

                        if any(orig_rubric.get(c) != edit_rubric.get(c) for c in all_criteria):
                             st.markdown("#### Rubric Changes")

                        for criterion in all_criteria:
                            orig_item = orig_rubric.get(criterion)
                            edit_item = edit_rubric.get(criterion)

                            if orig_item != edit_item:
                                st.markdown(f"##### _{criterion}_")
                                
                                orig_pts = orig_item.get('points', 0) if orig_item else 0
                                edit_pts = edit_item.get('points', 0) if edit_item else 0
                                if orig_pts != edit_pts:
                                    st.metric(label="Points", value=edit_pts, delta=f"{edit_pts - orig_pts:+.0f}")
                                
                                orig_reason = orig_item.get('reason', '') if orig_item else ''
                                edit_reason = edit_item.get('reason', '') if edit_item else ''
                                if orig_reason != edit_reason:
                                    render_text_diff("Feedback/Reason", orig_reason, edit_reason, f"reason_{i}_{criterion}")

            if not any_changes:
                st.success("✅ No changes detected.")

            st.markdown("---")
            b_col1, b_col2, _ = st.columns([1, 1, 3])
            with b_col1:
                if st.button("✅ Confirm and Submit All Grades to Canvas", use_container_width=True, type="primary"):
                    canvas = CanvasClient()
                    canvas.upload_all_scores(results["assignment_id"], edited_results)
                    cleanup_assignment_files(results["assignment_id"])
                    st.session_state["show_review_modal"] = False
                    st.success("✅ Grades successfully posted to Canvas and files deleted.")
                    st.session_state["show_return_dashboard"] = True
                    st.stop()
            with b_col2:
                if st.button("❌ Cancel Submission", use_container_width=True):
                    st.session_state["show_review_modal"] = False
                    st.rerun()

    # --- DISPLAY GRADING LOGS ---
    if "grading_logs" in st.session_state:
        logs = st.session_state["grading_logs"]
        error_lines = [line for line in logs if line.startswith("❌") or line.startswith("⚠️") or line.startswith("🔥")]
        if error_lines:
            st.markdown("### ⚠️ Grading Warnings & Errors")
            for line in error_lines:
                st.warning(line)
        log_text = "\n".join(logs)
        st.download_button("⬇️ Download Full Grading Log", log_text, file_name="grading_log.txt")

    # --- DISPLAY EXTRACTION FAILURES ---
    if "grading_results" in st.session_state:
        failures = st.session_state["grading_results"].get("extraction_failures", [])
        if failures:
            st.markdown("### ❗ Submissions Flagged for Manual Review (No Extractable Text)")
            failures_df = pd.DataFrame(failures)
            st.dataframe(failures_df)
            csv = failures_df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download Manual Review List", csv, file_name="extraction_failures.csv")

    if st.session_state.get("show_return_dashboard", False):
        st.markdown("---")
        st.markdown("### 🎯 What would you like to do next?")
        st.info("💡 **Tip:** You can grade another assignment right away, or return to the dashboard to manage your account settings.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🏠 Return to Dashboard", type="primary", use_container_width=True):
                # Clear all grading-related session state
                for key in [
                    "grading_results", "grading_logs", "overrides", "edited_results", "original_results", "show_review_modal", "show_return_dashboard"
                ]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        
        with col2:
            if st.button("🔄 Grade Another Assignment", type="secondary", use_container_width=True):
                # Clear all grading-related session state but keep user logged in
                for key in [
                    "grading_results", "grading_logs", "overrides", "edited_results", "original_results", "show_review_modal", "show_return_dashboard", "selected_assignment_id"
                ]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
