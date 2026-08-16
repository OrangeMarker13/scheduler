def validate_schedule(
    schedule,
    students,
    events,
    max_events,
):
    errors = []

    student_ids = {
        str(x)
        for x in students["student_id"]
    }

    event_lookup = events.set_index(
        "event_name"
    )

    student_event_counts = {}

    # -----------------------------------------------------
    # Check event teams.
    # -----------------------------------------------------

    for _, event in events.iterrows():

        event_name = event["event_name"]
        required_size = int(
            event["team_size"]
        )

        assigned = schedule.get(
            event_name,
            [],
        )

        if len(assigned) != required_size:

            errors.append(
                f"{event_name} requires "
                f"{required_size} students but has "
                f"{len(assigned)}."
            )

        for student_id in assigned:

            student_id = str(student_id)

            if student_id not in student_ids:

                errors.append(
                    f"Unknown student ID "
                    f"{student_id} assigned to "
                    f"{event_name}."
                )

            student_event_counts[
                student_id
            ] = (
                student_event_counts.get(
                    student_id,
                    0,
                )
                + 1
            )

    # -----------------------------------------------------
    # Event cap.
    # -----------------------------------------------------

    for student_id, count in student_event_counts.items():

        if count > max_events:

            errors.append(
                f"Student {student_id} has "
                f"{count} events. Maximum is "
                f"{max_events}."
            )

    # -----------------------------------------------------
    # Group conflicts.
    # -----------------------------------------------------

    groups = {}

    for _, event in events.iterrows():

        event_name = event["event_name"]

        groups.setdefault(
            event["conflict_group"],
            [],
        ).append(event_name)

    for student_id in student_ids:

        for group, group_events in groups.items():

            assigned_count = sum(
                student_id
                in schedule.get(
                    event_name,
                    [],
                )
                for event_name in group_events
            )

            if assigned_count > 1:

                errors.append(
                    f"Student {student_id} has "
                    f"multiple events in "
                    f"{group}."
                )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


def validate_change_request(
    request,
    students,
    events,
):
    student_id = str(
        request["student_id"]
    )

    valid_students = {
        str(x)
        for x in students["student_id"]
    }

    valid_events = set(
        events["event_name"]
    )

    if student_id not in valid_students:

        return {
            "valid": False,
            "message": "Selected student does not exist.",
        }

    event = request.get("event")

    if event and event not in valid_events:

        return {
            "valid": False,
            "message": "Selected event does not exist.",
        }

    target = request.get(
        "target_event"
    )

    if target and target not in valid_events:

        return {
            "valid": False,
            "message": "Target event does not exist.",
        }

    if (
        request["type"]
        == "Move student to event"
        and event == target
    ):

        return {
            "valid": False,
            "message": "Source and target events must be different.",
        }

    return {
        "valid": True,
        "message": "Valid change request.",
    }
