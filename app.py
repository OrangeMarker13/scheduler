import io
from copy import deepcopy

import pandas as pd
import streamlit as st

from scorer import build_student_profiles, build_capability_matrix
from optimizer import optimize_schedule
from quantum_optimizer import quantum_optimize_schedule
from validator import validate_schedule, validate_change_request
from sample_data import create_demo_data


st.set_page_config(
    page_title="SciOly Scheduler",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------
# Styling
# ---------------------------------------------------------

st.markdown(
    """
    <style>
    .stApp {
        background: #f5f7fb;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    .hero {
        background: linear-gradient(135deg, #101828, #243b53);
        padding: 30px;
        border-radius: 20px;
        color: white;
        margin-bottom: 24px;
    }

    .hero h1 {
        font-size: 42px;
        margin-bottom: 5px;
    }

    .hero p {
        color: #d0d5dd;
        font-size: 17px;
    }

    .metric-card {
        background: white;
        padding: 18px;
        border-radius: 15px;
        border: 1px solid #e4e7ec;
        box-shadow: 0 3px 12px rgba(16, 24, 40, 0.06);
    }

    .section-card {
        background: white;
        padding: 20px;
        border-radius: 18px;
        border: 1px solid #e4e7ec;
        margin-bottom: 18px;
    }

    .small-label {
        color: #667085;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: .05em;
    }

    .big-number {
        font-size: 30px;
        font-weight: 700;
        color: #101828;
    }

    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #e4e7ec;
        padding: 14px;
        border-radius: 14px;
    }

    .request-box {
        background: #f9fafb;
        border: 1px solid #d0d5dd;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def schedule_to_display(schedule, students):
    rows = []

    student_lookup = dict(
        zip(
            students["student_id"].astype(str),
            students["name"],
        )
    )

    for event_name, student_ids in schedule.items():
        names = [
            student_lookup.get(str(student_id), str(student_id))
            for student_id in student_ids
        ]

        rows.append(
            {
                "Event": event_name,
                "Students": ", ".join(names),
                "Team Size": len(names),
                "Student IDs": ", ".join(map(str, student_ids)),
            }
        )

    return pd.DataFrame(rows)


def assignment_dataframe(schedule, students):
    rows = []

    student_lookup = students.set_index("student_id")

    for event_name, student_ids in schedule.items():
        for student_id in student_ids:
            student_id = str(student_id)

            if student_id not in student_lookup.index:
                continue

            row = student_lookup.loc[student_id]

            rows.append(
                {
                    "Student": row["name"],
                    "Student ID": student_id,
                    "Grade": row["grade"],
                    "Tier": row["tier"],
                    "Event": event_name,
                }
            )

    return pd.DataFrame(rows)


def excel_bytes(schedule, students):
    schedule_df = schedule_to_display(schedule, students)
    assignments_df = assignment_dataframe(schedule, students)

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        schedule_df.to_excel(
            writer,
            index=False,
            sheet_name="Master Schedule",
        )

        assignments_df.to_excel(
            writer,
            index=False,
            sheet_name="Student Assignments",
        )

        students.to_excel(
            writer,
            index=False,
            sheet_name="Students",
        )

    output.seek(0)
    return output.getvalue()


def calculate_statistics(schedule, students):
    total_assignments = sum(len(v) for v in schedule.values())

    counts = {}

    for event_students in schedule.values():
        for student_id in event_students:
            counts[str(student_id)] = counts.get(str(student_id), 0) + 1

    if counts:
        average = total_assignments / len(counts)
        maximum = max(counts.values())
        minimum = min(counts.values())
    else:
        average = 0
        maximum = 0
        minimum = 0

    return {
        "assignments": total_assignments,
        "average": average,
        "maximum": maximum,
        "minimum": minimum,
        "students_used": len(counts),
    }


def initialize_demo():
    students, scores, events = create_demo_data()

    profiles = build_student_profiles(students, scores)
    capability = build_capability_matrix(
        profiles,
        events,
    )

    st.session_state.students = profiles
    st.session_state.events = events
    st.session_state.capability = capability
    st.session_state.schedule = None
    st.session_state.original_schedule = None
    st.session_state.change_requests = []


# ---------------------------------------------------------
# Session initialization
# ---------------------------------------------------------

if "students" not in st.session_state:
    initialize_demo()


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

st.markdown(
    """
    <div class="hero">
        <div class="small-label">Science Olympiad Operations</div>
        <h1>Team Scheduler</h1>
        <p>
            Build balanced tournament lineups using student performance,
            preferences, experience, event conflicts, and optimization.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

with st.sidebar:
    st.header("Scheduler Controls")

    data_mode = st.radio(
        "Data source",
        [
            "Demo Data",
            "Upload CSV",
        ],
    )

    max_events = st.slider(
        "Maximum events per student",
        min_value=1,
        max_value=6,
        value=5,
    )

    varsity_percent = st.slider(
        "Varsity percentage",
        min_value=25,
        max_value=90,
        value=60,
        step=5,
    )

    st.divider()

    st.subheader("Optimization")

    quantum_enabled = st.toggle(
        "Use quantum optimization",
        value=True,
    )

    if quantum_enabled:
        st.caption(
            "The app attempts QAOA first and falls back to classical optimization when needed."
        )

    st.divider()

    if st.button("Reset Demo", use_container_width=True):
        initialize_demo()
        st.rerun()


# ---------------------------------------------------------
# Data loading
# ---------------------------------------------------------

if data_mode == "Upload CSV":

    st.subheader("Upload Team Data")

    c1, c2, c3 = st.columns(3)

    with c1:
        students_file = st.file_uploader(
            "students.csv",
            type=["csv"],
        )

    with c2:
        scores_file = st.file_uploader(
            "scores.csv",
            type=["csv"],
        )

    with c3:
        events_file = st.file_uploader(
            "events.csv",
            type=["csv"],
        )

    if students_file and scores_file and events_file:

        try:
            raw_students = pd.read_csv(students_file)
            raw_scores = pd.read_csv(scores_file)
            events = pd.read_csv(events_file)

            profiles = build_student_profiles(
                raw_students,
                raw_scores,
                varsity_percent=varsity_percent,
            )

            capability = build_capability_matrix(
                profiles,
                events,
            )

            st.session_state.students = profiles
            st.session_state.events = events
            st.session_state.capability = capability

            st.success("Team data loaded successfully.")

        except Exception as exc:
            st.error(f"Could not load the uploaded data: {exc}")


students = st.session_state.students
events = st.session_state.events
capability = st.session_state.capability


# ---------------------------------------------------------
# Overview
# ---------------------------------------------------------

st.subheader("Team Overview")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        "Students",
        len(students),
    )

with c2:
    st.metric(
        "Events",
        len(events),
    )

with c3:
    st.metric(
        "Varsity",
        int((students["tier"] == "Varsity").sum()),
    )

with c4:
    st.metric(
        "JV",
        int((students["tier"] == "JV").sum()),
    )


# ---------------------------------------------------------
# Main navigation
# ---------------------------------------------------------

tabs = st.tabs(
    [
        "📅 Schedule",
        "🔧 Change Requests",
        "👥 Students",
        "📊 Analytics",
    ]
)


# ---------------------------------------------------------
# Schedule
# ---------------------------------------------------------

with tabs[0]:

    st.subheader("Master Schedule")

    if st.session_state.schedule is None:

        st.info(
            "Your team data is ready. Generate an optimized schedule to begin."
        )

        if st.button(
            "⚡ Generate Optimal Schedule",
            type="primary",
            use_container_width=True,
        ):

            with st.spinner("Optimizing the tournament lineup..."):

                classical = optimize_schedule(
                    students=students,
                    events=events,
                    capability=capability,
                    max_events=max_events,
                )

                if quantum_enabled:
                    schedule, method = quantum_optimize_schedule(
                        students=students,
                        events=events,
                        capability=capability,
                        max_events=max_events,
                        classical_schedule=classical,
                    )
                else:
                    schedule = classical
                    method = "OR-Tools"

                validation = validate_schedule(
                    schedule,
                    students,
                    events,
                    max_events,
                )

                if not validation["valid"]:
                    st.error(
                        "The optimizer returned an invalid schedule."
                    )

                    for error in validation["errors"]:
                        st.error(error)

                else:
                    st.session_state.schedule = schedule
                    st.session_state.original_schedule = deepcopy(schedule)

                    st.success(
                        f"Schedule generated using {method}."
                    )

                    st.rerun()

    else:

        stats = calculate_statistics(
            st.session_state.schedule,
            students,
        )

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric(
                "Assignments",
                stats["assignments"],
            )

        with c2:
            st.metric(
                "Students Used",
                stats["students_used"],
            )

        with c3:
            st.metric(
                "Average Events",
                f"{stats['average']:.1f}",
            )

        with c4:
            st.metric(
                "Max Events",
                stats["maximum"],
            )

        schedule_df = schedule_to_display(
            st.session_state.schedule,
            students,
        )

        st.dataframe(
            schedule_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Event": st.column_config.TextColumn(
                    "Event",
                    width="large",
                ),
                "Students": st.column_config.TextColumn(
                    "Assigned Students",
                    width="large",
                ),
                "Team Size": st.column_config.NumberColumn(
                    "Team Size",
                ),
                "Student IDs": st.column_config.TextColumn(
                    "IDs",
                ),
            },
        )

        validation = validate_schedule(
            st.session_state.schedule,
            students,
            events,
            max_events,
        )

        if validation["valid"]:
            st.success("✓ Schedule passes all hard constraints.")

        else:
            st.error("Schedule contains constraint violations.")

            for error in validation["errors"]:
                st.error(error)

        excel_data = excel_bytes(
            st.session_state.schedule,
            students,
        )

        st.download_button(
            "⬇ Download Schedule as Excel",
            data=excel_data,
            file_name="science_olympiad_schedule.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


# ---------------------------------------------------------
# Change Requests
# ---------------------------------------------------------

with tabs[1]:

    st.subheader("Change Requests")

    st.write(
        "Submit all requested changes first. The optimizer then searches for the best schedule satisfying the requests."
    )

    if "change_requests" not in st.session_state:
        st.session_state.change_requests = []

    request_type = st.selectbox(
        "Request type",
        [
            "Move student to event",
            "Remove student from event",
            "Keep student in event",
        ],
    )

    student_names = students["name"].tolist()

    selected_student_name = st.selectbox(
        "Student",
        student_names,
    )

    selected_student_id = str(
        students.loc[
            students["name"] == selected_student_name,
            "student_id",
        ].iloc[0]
    )

    selected_event = st.selectbox(
        "Event",
        events["event_name"].tolist(),
    )

    if request_type == "Move student to event":

        target_event = st.selectbox(
            "Move to",
            [
                e
                for e in events["event_name"].tolist()
                if e != selected_event
            ],
        )

    else:
        target_event = None

    priority = st.selectbox(
        "Priority",
        [
            "Required",
            "High",
            "Medium",
            "Low",
        ],
    )

    if st.button(
        "＋ Add Change Request",
        use_container_width=True,
    ):

        request = {
            "type": request_type,
            "student_id": selected_student_id,
            "student": selected_student_name,
            "event": selected_event,
            "target_event": target_event,
            "priority": priority,
        }

        validation = validate_change_request(
            request,
            students,
            events,
        )

        if validation["valid"]:
            st.session_state.change_requests.append(request)
            st.success("Change request added.")
            st.rerun()

        else:
            st.error(validation["message"])

    st.divider()

    if st.session_state.change_requests:

        st.subheader("Pending Requests")

        for i, request in enumerate(
            st.session_state.change_requests
        ):

            target = request["target_event"]

            if target:
                description = (
                    f"{request['student']} → {target}"
                )
            else:
                description = (
                    f"{request['student']} / {request['event']}"
                )

            c1, c2 = st.columns([6, 1])

            with c1:
                st.markdown(
                    f"""
                    <div class="request-box">
                        <b>Request {i + 1}</b><br>
                        {request["type"]}<br>
                        {description}<br>
                        Priority: {request["priority"]}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with c2:
                if st.button(
                    "Remove",
                    key=f"remove_request_{i}",
                ):
                    st.session_state.change_requests.pop(i)
                    st.rerun()

        st.divider()

        if st.session_state.schedule is None:
            st.warning(
                "Generate an initial schedule before optimizing change requests."
            )

        else:

            if st.button(
                "🧠 Optimize All Change Requests",
                type="primary",
                use_container_width=True,
            ):

                with st.spinner(
                    "Searching for the best revised schedule..."
                ):

                    optimized = optimize_schedule(
                        students=students,
                        events=events,
                        capability=capability,
                        max_events=max_events,
                        change_requests=st.session_state.change_requests,
                        previous_schedule=st.session_state.schedule,
                    )

                    validation = validate_schedule(
                        optimized,
                        students,
                        events,
                        max_events,
                    )

                    if validation["valid"]:

                        st.session_state.schedule = optimized

                        st.success(
                            "A valid revised schedule was found."
                        )

                        st.rerun()

                    else:

                        st.error(
                            "No valid schedule satisfying all required constraints was found."
                        )

                        for error in validation["errors"]:
                            st.error(error)

    else:

        st.info(
            "No change requests have been added."
        )


# ---------------------------------------------------------
# Students
# ---------------------------------------------------------

with tabs[2]:

    st.subheader("Student Profiles")

    display_columns = [
        "student_id",
        "name",
        "grade",
        "composite_score",
        "tier",
    ]

    available_columns = [
        c
        for c in display_columns
        if c in students.columns
    ]

    st.dataframe(
        students[available_columns],
        use_container_width=True,
        hide_index=True,
    )


# ---------------------------------------------------------
# Analytics
# ---------------------------------------------------------

with tabs[3]:

    st.subheader("Schedule Analytics")

    if st.session_state.schedule is None:

        st.info(
            "Generate a schedule to view analytics."
        )

    else:

        schedule = st.session_state.schedule

        assignment_counts = {}

        for event_students in schedule.values():
            for student_id in event_students:
                assignment_counts[str(student_id)] = (
                    assignment_counts.get(str(student_id), 0) + 1
                )

        analytics_rows = []

        for _, student in students.iterrows():

            student_id = str(student["student_id"])

            analytics_rows.append(
                {
                    "Student": student["name"],
                    "Tier": student["tier"],
                    "Events": assignment_counts.get(
                        student_id,
                        0,
                    ),
                    "Composite Score": round(
                        student["composite_score"],
                        1,
                    ),
                }
            )

        analytics_df = pd.DataFrame(
            analytics_rows
        )

        st.dataframe(
            analytics_df,
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Event Distribution")

        event_counts = pd.DataFrame(
            [
                {
                    "Event": event,
                    "Students": len(student_ids),
                }
                for event, student_ids in schedule.items()
            ]
        )

        st.bar_chart(
            event_counts.set_index("Event")
        )
