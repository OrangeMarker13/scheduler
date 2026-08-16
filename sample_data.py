import random

import pandas as pd


EVENTS = [
    ("Anatomy & Physiology", "Biology", "Group 1", 2),
    ("Disease Detectives", "Biology", "Group 1", 2),
    ("Heredity", "Biology", "Group 1", 2),
    ("Botany", "Biology", "Group 1", 2),
    ("Water Quality", "Chemistry", "Group 1", 2),

    ("Dynamic Planet", "Earth & Space", "Group 2", 2),
    ("Meteorology", "Earth & Space", "Group 2", 2),
    ("Remote Sensing", "Earth & Space", "Group 2", 2),
    ("Rocks & Minerals", "Earth & Space", "Group 2", 2),
    ("Solar System", "Earth & Space", "Group 2", 2),

    ("Hovercraft", "Build", "Group 3", 2),
    ("Circuit Lab", "Physics", "Group 3", 2),
    ("Thermodynamics", "Physics", "Group 3", 2),
    ("Crime Busters", "Chemistry", "Group 3", 2),
    ("Food Science", "Chemistry", "Group 3", 2),

    ("Boomilever", "Build", "Group 4", 2),
    ("Elastic Launch Glider", "Build", "Group 4", 2),
    ("Roller Coaster", "Build", "Group 4", 2),
    ("Scrambler", "Build", "Group 4", 2),

    ("Codebusters", "Inquiry", "Group 5", 3),
    ("Experimental Design", "Inquiry", "Group 5", 3),
    ("Ping Pong Parachute", "Build", "Group 5", 2),
    ("Write It Do It", "Inquiry", "Group 5", 2),

    ("Code Craze", "Inquiry", "Group 6", 2),
    ("Protein Modeling", "Biology", "Group 6", 2),
]


FIRST_NAMES = [
    "Alex",
    "Maya",
    "Ryan",
    "Sarah",
    "Daniel",
    "Emma",
    "Noah",
    "Ava",
    "Ethan",
    "Sophia",
    "Lucas",
    "Olivia",
    "Henry",
    "Isabella",
    "James",
    "Amelia",
    "Benjamin",
    "Charlotte",
    "Michael",
    "Harper",
]


LAST_NAMES = [
    "Johnson",
    "Patel",
    "Chen",
    "Williams",
    "Garcia",
    "Smith",
    "Brown",
    "Davis",
    "Miller",
    "Wilson",
    "Anderson",
    "Thomas",
    "Moore",
    "Jackson",
    "Martin",
    "Lee",
    "Walker",
    "Hall",
    "Allen",
    "Young",
]


def create_demo_data():
    random.seed(42)

    students = []

    for i in range(20):

        students.append(
            {
                "student_id": str(
                    i + 1
                ),
                "name": (
                    f"{FIRST_NAMES[i]} "
                    f"{LAST_NAMES[i]}"
                ),
                "grade": random.choice(
                    [8, 9]
                ),
                "past_experience_points": random.randint(
                    0,
                    10,
                ),
                "pref_1": "",
                "pref_2": "",
                "pref_3": "",
                "pref_4": "",
                "pref_5": "",
            }
        )

    students_df = pd.DataFrame(
        students
    )

    event_names = [
        event[0]
        for event in EVENTS
    ]

    for i in range(len(students_df)):

        preferences = random.sample(
            event_names,
            5,
        )

        for rank in range(1, 6):

            students_df.loc[
                i,
                f"pref_{rank}",
            ] = preferences[
                rank - 1
            ]

    scores = []

    for i in range(20):

        scores.append(
            {
                "student_id": str(i + 1),
                "physics_score": random.randint(
                    55,
                    100,
                ),
                "chem_score": random.randint(
                    55,
                    100,
                ),
                "bio_score": random.randint(
                    55,
                    100,
                ),
                "build_score": random.randint(
                    55,
                    100,
                ),
                "earth_space_score": random.randint(
                    55,
                    100,
                ),
            }
        )

    scores_df = pd.DataFrame(
        scores
    )

    events_df = pd.DataFrame(
        [
            {
                "event_name": event[0],
                "category": event[1],
                "conflict_group": event[2],
                "team_size": event[3],
            }
            for event in EVENTS
        ]
    )

    return (
        students_df,
        scores_df,
        events_df,
    )
