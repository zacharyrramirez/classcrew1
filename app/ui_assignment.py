import streamlit as st
from canvas.client import CanvasClient
from utils.file_ops import get_submission_status
from datetime import datetime

def format_due_date(due_str):
    if due_str is None:
        return "No Due Date"
    try:
        return datetime.fromisoformat(due_str.replace("Z", "+00:00")).strftime("%b %d, %Y")
    except Exception:
        return "Invalid Date"

@st.cache_data(ttl=300)
def load_assignments():
    try:
        canvas = CanvasClient()
        return canvas.get_assignments(filter_by="all")
    except Exception as e:
        # Surface clearer guidance for common configuration issues
        st.error("Couldn't load assignments from Canvas.\n\nCheck: Canvas URL, API token, and Course ID in your account settings.")
        raise

@st.cache_data(ttl=300)
def load_submission_stats(assignment_id):
    canvas = CanvasClient()
    subs = canvas.get_submissions(assignment_id)
    stats = {
        "On Time": 0, "Late": 0, "Missing": 0, "Resubmitted": 0
    }
    # Only use metadata for status counts
    for sub in subs:
        status = get_submission_status(sub)
        if status in stats:
            stats[status] += 1
    return stats

def render_assignment_selection():
    st.set_page_config(page_title="Classcrew AI Grader", layout="wide")

    st.markdown("""
Welcome to your AI-powered grading system.    
- **Anonymizes** students before grading  
- Uses **LLMs** to generate rubric-aligned feedback and scores  
- Includes a **fairness review** to catch flawed AI results (with automatic regrading if needed)  
- Grades are **only posted to Canvas after your approval**.  
- **All temporary files are securely deleted** after grade posting.
    """)

    assignments = load_assignments()
    assignments = sorted(assignments, key=lambda a: a.get("due_at") or "")

    if not assignments:
        st.error("⚠️ No assignments available.")
        st.stop()

    assignment_options = {
        f"{a['name']} — due {format_due_date(a['due_at'])}": a["id"]
        for a in assignments
    }

    assignment_label = st.selectbox("🎯 Choose an assignment to grade:", list(assignment_options.keys()))
    # Keep assignment_id as an integer for Canvas API calls
    try:
        assignment_id = int(assignment_options[assignment_label])
    except Exception:
        st.error("Invalid assignment selection. Please reload and try again.")
        st.stop()

    # Load submission stats only after selection
    with st.spinner("🔄 Loading submission stats..."):
        try:
            stats = load_submission_stats(assignment_id)
        except Exception as e:
            st.error("Couldn't load submissions for this assignment.\n\nPlease verify your Canvas Course ID, the assignment exists in that course, and your API token has access.")
            st.stop()
        st.markdown(f"""<div style='display: flex; gap: 1.5rem; font-size: 1.1rem; margin-top: 0.5rem;'>
    <span>⚪ <b>{stats["On Time"]}</b> On Time</span>
    <span>🔵 <b>{stats["Late"]}</b> Late</span>
    <span>🟢 <b>{stats["Resubmitted"]}</b> Resubmitted</span>
    <span>🔴 <b>{stats["Missing"]}</b> Missing</span>
</div>""", unsafe_allow_html=True)

    # Fetch all submissions for this assignment
    canvas = CanvasClient()
    try:
        all_submissions = canvas.get_submissions(assignment_id, filter_by="all")
    except Exception as e:
        st.error(f"Canvas error fetching submissions for assignment {assignment_id}: {e}")
        st.stop()
    graded = [s for s in all_submissions if s.get("workflow_state") == "graded"]
    ungraded = [s for s in all_submissions if s.get("workflow_state") != "graded"]

    st.markdown(f"**Graded:** {len(graded)} | **Ungraded:** {len(ungraded)} | **Total:** {len(all_submissions)}")
    submission_filter = st.radio(
        "Which submissions do you want to grade?",
        ("All", "Only ungraded", "Only graded (regrade)")
    )
    if submission_filter == "Only ungraded":
        filtered_submissions = ungraded
    elif submission_filter == "Only graded (regrade)":
        filtered_submissions = graded
    else:
        filtered_submissions = all_submissions

    try:
        rubric_items = CanvasClient().get_rubric(assignment_id)
    except Exception as e:
        st.warning(f"Couldn't fetch rubric for assignment {assignment_id}. Proceeding without rubric. Error: {e}")
        rubric_items = []
    with st.expander("📋 Preview: Full Rubric for This Assignment", expanded=False):
        if not rubric_items:
            st.warning("⚠️ No rubric found for this assignment on Canvas.")
        else:
            for item in rubric_items:
                st.markdown(f"**{item['criterion']}** ({item['max_points']} pts)")
                if item.get("description"):
                    st.markdown(f":small_blue_diamond: _{item['description']}_")
                if item.get("ratings"):
                    for rating in item["ratings"]:
                        st.markdown(f"- **{rating['description']}** ({rating['points']} pts): {rating.get('long_description', '')}")
                st.markdown("---")

    return assignment_id, rubric_items, assignment_options, submission_filter, filtered_submissions
