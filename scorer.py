import math
import numpy as np
import pandas as pd


SUBJECT_COLUMNS = {
    "Physics": "physics_score",
    "Chemistry": "chem_score",
    "Biology": "bio_score",
    "Build": "build_score",
    "Earth & Space": "earth_space_score",
}


EVENT_SUBJECTS = {
    "Anatomy & Physiology": ["Biology"],
    "Disease Detectives": ["Biology"],
    "Heredity": ["Biology"],
    "Botany": ["Biology"],
    "Water Quality": ["Chemistry", "Earth & Space"],

    "Dynamic Planet": ["Earth & Space"],
    "Meteorology": ["Earth & Space"],
    "Remote Sensing": ["Earth & Space"],
    "Rocks & Minerals": ["Earth & Space"],
    "Solar System": ["Earth & Space"],

    "Hovercraft": ["Physics", "Build"],
    "Circuit Lab": ["Physics"],
    "Thermodynamics": ["Physics", "Chemistry"],
    "Crime Busters": ["Chemistry", "Biology"],
    "Food Science": ["Chemistry", "Biology"],

    "Boomilever": ["Build"],
    "Elastic Launch Glider": ["Physics", "Build"],
    "Roller Coaster": ["Physics", "Build"],
    "Scrambler": ["Physics", "Build"],

    "Codebusters": ["Physics", "Chemistry"],
    "Experimental Design": [
        "Physics",
        "Chemistry",
        "Biology",
        "Earth & Space",
    ],
    "Ping Pong Parachute": ["Physics", "Build"],
    "Write It Do It": ["Biology"],

    "Code Craze": ["Physics"],
    "Protein Modeling": ["Biology", "Chemistry"],
}


def normalize(series):
    series = pd.to_numeric(
        series,
        errors="coerce",
    ).fillna(0)

    minimum = series.min()
    maximum = series.max()

    if maximum == minimum:
        return pd.Series(
            np.full(len(series), 50.0),
            index=series.index,
        )

    return (
        (series - minimum)
        / (maximum - minimum)
        * 100
    )


def build_student_profiles(
    students,
    scores,
    varsity_percent=60,
):
    students = students.copy()
    scores = scores.copy()

    students["student_id"] = (
        students["student_id"]
        .astype(str)
    )

    scores["student_id"] = (
        scores["student_id"]
        .astype(str)
    )

    merged = students.merge(
        scores,
        on="student_id",
        how="left",
    )

    score_columns = [
        "physics_score",
        "chem_score",
        "bio_score",
        "build_score",
        "earth_space_score",
    ]

    for column in score_columns:

        if column not in merged:
            merged[column] = 0

        merged[column] = pd.to_numeric(
            merged[column],
            errors="coerce",
        ).fillna(0)

        merged[column] = merged[column].clip(
            0,
            100,
        )

    experience = pd.to_numeric(
        merged.get(
            "past_experience_points",
            0,
        ),
        errors="coerce",
    ).fillna(0)

    experience_normalized = normalize(
        experience
    )

    merged["experience_score"] = (
        experience_normalized
    )

    merged["composite_score"] = (
        merged["physics_score"] * 0.18
        + merged["chem_score"] * 0.18
        + merged["bio_score"] * 0.22
        + merged["build_score"] * 0.18
        + merged["earth_space_score"] * 0.14
        + merged["experience_score"] * 0.10
    )

    merged["composite_score"] = merged[
        "composite_score"
    ].clip(0, 100)

    ranking = merged[
        "composite_score"
    ].rank(
        method="first",
        ascending=False,
    )

    varsity_count = max(
        1,
        math.ceil(
            len(merged)
            * varsity_percent
            / 100
        ),
    )

    merged["tier"] = np.where(
        ranking <= varsity_count,
        "Varsity",
        "JV",
    )

    return merged


def preference_score(student, event_name):
    scores = {
        1: 100,
        2: 75,
        3: 50,
        4: 30,
        5: 15,
    }

    for rank in range(1, 6):

        column = f"pref_{rank}"

        if column in student:

            value = str(
                student[column]
            ).strip().lower()

            if value == event_name.lower():
                return scores[rank]

    return 0


def skill_score(student, event_name):

    subjects = EVENT_SUBJECTS.get(
        event_name,
        [],
    )

    if not subjects:
        return 50

    values = []

    for subject in subjects:

        column = SUBJECT_COLUMNS.get(
            subject
        )

        if column and column in student:
            values.append(
                float(student[column])
            )

    if not values:
        return 50

    return float(np.mean(values))


def build_capability_matrix(
    students,
    events,
):
    rows = []

    for _, student in students.iterrows():

        for _, event in events.iterrows():

            event_name = event["event_name"]

            preference = preference_score(
                student,
                event_name,
            )

            skill = skill_score(
                student,
                event_name,
            )

            tier_bonus = (
                10
                if student["tier"] == "Varsity"
                else 0
            )

            total_score = (
                skill * 0.65
                + preference * 0.25
                + tier_bonus
            )

            rows.append(
                {
                    "student_id": str(
                        student["student_id"]
                    ),
                    "event_name": event_name,
                    "skill_score": skill,
                    "preference_score": preference,
                    "total_score": total_score,
                }
            )

    return pd.DataFrame(rows)
