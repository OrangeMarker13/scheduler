from collections import defaultdict

from ortools.sat.python import cp_model


PRIORITY_WEIGHT = {
    "Required": 10000,
    "High": 1000,
    "Medium": 100,
    "Low": 10,
}


def optimize_schedule(
    students,
    events,
    capability,
    max_events=5,
    change_requests=None,
    previous_schedule=None,
):
    change_requests = change_requests or {}

    if isinstance(change_requests, list):
        requests = change_requests
    else:
        requests = []

    model = cp_model.CpModel()

    student_ids = [
        str(x)
        for x in students["student_id"]
    ]

    event_names = [
        x
        for x in events["event_name"]
    ]

    event_info = events.set_index(
        "event_name"
    ).to_dict("index")

    variables = {}

    for student_id in student_ids:

        for event_name in event_names:

            variables[
                student_id,
                event_name
            ] = model.NewBoolVar(
                f"x_{student_id}_{event_name}"
            )

    # -----------------------------------------------------
    # Each event receives exactly its required team size.
    # -----------------------------------------------------

    for event_name in event_names:

        team_size = int(
            event_info[event_name][
                "team_size"
            ]
        )

        model.Add(
            sum(
                variables[
                    student_id,
                    event_name,
                ]
                for student_id in student_ids
            )
            == team_size
        )

    # -----------------------------------------------------
    # A student cannot exceed max events.
    # -----------------------------------------------------

    for student_id in student_ids:

        model.Add(
            sum(
                variables[
                    student_id,
                    event_name,
                ]
                for event_name in event_names
            )
            <= max_events
        )

    # -----------------------------------------------------
    # Group conflict constraint.
    # -----------------------------------------------------

    groups = defaultdict(list)

    for _, event in events.iterrows():

        groups[
            str(event["conflict_group"])
        ].append(
            event["event_name"]
        )

    for student_id in student_ids:

        for group_events in groups.values():

            model.Add(
                sum(
                    variables[
                        student_id,
                        event_name,
                    ]
                    for event_name in group_events
                )
                <= 1
            )

    # -----------------------------------------------------
    # Workload diversity.
    # No student gets more than 2 events
    # from the same broad category.
    # -----------------------------------------------------

    categories = defaultdict(list)

    for _, event in events.iterrows():

        categories[
            str(event["category"])
        ].append(
            event["event_name"]
        )

    for student_id in student_ids:

        for category_events in categories.values():

            model.Add(
                sum(
                    variables[
                        student_id,
                        event_name,
                    ]
                    for event_name in category_events
                )
                <= 2
            )

    # -----------------------------------------------------
    # Objective.
    # -----------------------------------------------------

    capability_lookup = {}

    for _, row in capability.iterrows():

        capability_lookup[
            (
                str(row["student_id"]),
                row["event_name"],
            )
        ] = float(
            row["total_score"]
        )

    objective_terms = []

    for student_id in student_ids:

        for event_name in event_names:

            score = capability_lookup.get(
                (
                    student_id,
                    event_name,
                ),
                0,
            )

            objective_terms.append(
                variables[
                    student_id,
                    event_name,
                ]
                * int(score * 100)
            )

    # -----------------------------------------------------
    # Change requests.
    # -----------------------------------------------------

    for request in requests:

        student_id = str(
            request["student_id"]
        )

        request_type = request["type"]
        priority = request["priority"]

        weight = PRIORITY_WEIGHT.get(
            priority,
            10,
        )

        if request_type == "Move student to event":

            target = request[
                "target_event"
            ]

            model.Add(
                variables[
                    student_id,
                    target,
                ]
                == 1
            )

        elif request_type == "Keep student in event":

            event_name = request["event"]

            model.Add(
                variables[
                    student_id,
                    event_name,
                ]
                == 1
            )

        elif request_type == "Remove student from event":

            event_name = request["event"]

            model.Add(
                variables[
                    student_id,
                    event_name,
                ]
                == 0
            )

    model.Maximize(
        sum(objective_terms)
    )

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = 15
    solver.parameters.num_search_workers = 8

    status = solver.Solve(model)

    if status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    ):
        raise RuntimeError(
            "No feasible schedule satisfies the current constraints."
        )

    schedule = {
        event_name: []
        for event_name in event_names
    }

    for student_id in student_ids:

        for event_name in event_names:

            if solver.Value(
                variables[
                    student_id,
                    event_name,
                ]
            ):

                schedule[
                    event_name
                ].append(
                    student_id
                )

    return schedule
