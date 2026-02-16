from datetime import datetime, timedelta
from itertools import combinations

from models import Match, Schedule, ScheduleRequest


def round_robin_order(n: int) -> list[list[tuple[int, int]]]:
    """Generate pairs in round-robin tournament order (circle method).

    Returns a list of rounds, each containing pairs of team indices.
    """
    teams = list(range(n))
    if n % 2 == 1:
        teams.append(-1)  # bye placeholder

    rounds = []
    for _ in range(len(teams) - 1):
        round_pairs = []
        for i in range(len(teams) // 2):
            t1 = teams[i]
            t2 = teams[-(i + 1)]
            if t1 != -1 and t2 != -1:
                round_pairs.append((min(t1, t2), max(t1, t2)))
        rounds.append(round_pairs)
        # Rotate: fix teams[0], rotate the rest
        teams.insert(1, teams.pop())

    return rounds


def generate_schedule(request: ScheduleRequest) -> Schedule:
    n = request.num_teams
    num_fields = request.num_fields
    config = request.get_config()

    # Default team names
    if request.team_names and len(request.team_names) == n:
        team_names = request.team_names
    else:
        team_names = [f"Team {i + 1}" for i in range(n)]

    # All pairs to schedule
    all_pairs = list(combinations(range(n), 2))

    # Max simultaneous matches per slot: limited by fields and need for 3 teams per match
    max_simultaneous = min(num_fields, n // 3)
    if max_simultaneous < 1:
        max_simultaneous = 1

    # Get round-robin ordered pairs for better distribution
    rounds = round_robin_order(n)
    ordered_pairs = []
    for r in rounds:
        for pair in r:
            ordered_pairs.append(pair)

    # Verify all pairs are covered
    assert set(ordered_pairs) == set(all_pairs)

    # Greedy slot filling
    unscheduled = list(ordered_pairs)
    slots: list[list[tuple[int, int, int, int]]] = []  # (t1, t2, ref, field)
    referee_counts = {i: 0 for i in range(n)}
    has_played = set()  # teams that have played at least once
    warnings = []

    while unscheduled:
        current_slot = []
        busy_teams: set[int] = set()
        slot_index = len(slots)

        # For early-start: prioritize pairs with teams that haven't played yet
        if slot_index < 2:
            unscheduled.sort(
                key=lambda p: (
                    p[0] in has_played and p[1] in has_played,
                    min(referee_counts[p[0]], referee_counts[p[1]]),
                )
            )

        scheduled_this_slot = []
        for pair in unscheduled:
            if len(current_slot) >= max_simultaneous:
                break

            t1, t2 = pair
            if t1 in busy_teams or t2 in busy_teams:
                continue

            # Find best referee
            candidates = [
                t for t in range(n) if t not in busy_teams and t != t1 and t != t2
            ]
            if not candidates:
                continue

            referee = min(candidates, key=lambda t: referee_counts[t])
            field_num = len(current_slot) + 1

            current_slot.append((t1, t2, referee, field_num))
            busy_teams.update({t1, t2, referee})
            has_played.update({t1, t2})
            referee_counts[referee] += 1
            scheduled_this_slot.append(pair)

        for pair in scheduled_this_slot:
            unscheduled.remove(pair)

        if not current_slot:
            # Safety: avoid infinite loop if something goes wrong
            warnings.append(
                "Could not schedule all matches. Some matches may be missing."
            )
            break

        slots.append(current_slot)

    # Check early-start constraint
    teams_not_played_by_slot2 = set(range(n)) - has_played
    if teams_not_played_by_slot2:
        names = [team_names[t] for t in teams_not_played_by_slot2]
        warnings.append(f"Teams not playing in first 2 slots: {', '.join(names)}")

    # More precise early-start check: look at actual slot assignments
    first_play_slot = {i: None for i in range(n)}
    for slot_idx, slot in enumerate(slots):
        for t1, t2, _ref, _field in slot:
            if first_play_slot[t1] is None:
                first_play_slot[t1] = slot_idx
            if first_play_slot[t2] is None:
                first_play_slot[t2] = slot_idx

    late_starters = [
        team_names[t]
        for t in range(n)
        if first_play_slot[t] is not None and first_play_slot[t] > 1
    ]
    if late_starters:
        warnings.append(f"Teams starting after slot 2: {', '.join(late_starters)}")

    # Build Match objects with times
    base_time = datetime.strptime(request.start_time, "%H:%M")
    matches = []
    match_num = 1

    for slot_idx, slot in enumerate(slots):
        slot_time = base_time + timedelta(minutes=slot_idx * config.slot_duration)
        time_str = slot_time.strftime("%H:%M")

        for t1, t2, ref, field_num in slot:
            matches.append(
                Match(
                    match_number=match_num,
                    team1=team_names[t1],
                    team2=team_names[t2],
                    referee=team_names[ref],
                    field_number=field_num,
                    time_slot=slot_idx,
                    start_time=time_str,
                )
            )
            match_num += 1

    # Compute stats
    stats = {}
    for i in range(n):
        name = team_names[i]
        played = sum(1 for m in matches if m.team1 == name or m.team2 == name)
        refereed = referee_counts[i]
        stats[name] = {"played": played, "refereed": refereed}

    return Schedule(
        category=request.category,
        matches=matches,
        warnings=warnings,
        stats=stats,
    )


if __name__ == "__main__":
    # Test with various configurations
    for category in ["U8", "U10", "U12"]:
        for num_teams in range(3, 9):
            for num_fields in [1, 2, 3]:
                req = ScheduleRequest(
                    category=category,
                    num_teams=num_teams,
                    num_fields=num_fields,
                    start_time="09:00",
                )
                sched = generate_schedule(req)
                total_expected = num_teams * (num_teams - 1) // 2

                # Verify all matches scheduled
                assert len(sched.matches) == total_expected, (
                    f"{category} {num_teams}t {num_fields}f: "
                    f"expected {total_expected}, got {len(sched.matches)}"
                )

                # Verify no duplicate matchups
                pairs = set()
                for m in sched.matches:
                    pair = tuple(sorted([m.team1, m.team2]))
                    assert pair not in pairs, f"Duplicate: {pair}"
                    pairs.add(pair)

                # Verify no time conflicts
                for slot_idx in range(max(m.time_slot for m in sched.matches) + 1):
                    slot_matches = [m for m in sched.matches if m.time_slot == slot_idx]
                    teams_in_slot = []
                    for m in slot_matches:
                        teams_in_slot.extend([m.team1, m.team2, m.referee])
                    assert len(teams_in_slot) == len(set(teams_in_slot)), (
                        f"Time conflict in {category} {num_teams}t {num_fields}f slot {slot_idx}"
                    )

                status = "OK"
                if sched.warnings:
                    status = f"WARN: {'; '.join(sched.warnings)}"
                print(
                    f"{category} | {num_teams} teams | {num_fields} fields | "
                    f"{len(sched.matches)} matches | {len(set(m.time_slot for m in sched.matches))} slots | {status}"
                )

    # Print a sample schedule
    print("\n--- Sample: U10, 6 teams, 2 fields ---")
    req = ScheduleRequest(
        category="U10",
        num_teams=6,
        num_fields=2,
        start_time="09:00",
        team_names=["Lions", "Tigers", "Bears", "Eagles", "Hawks", "Wolves"],
    )
    sched = generate_schedule(req)
    current_slot = -1
    for m in sched.matches:
        if m.time_slot != current_slot:
            current_slot = m.time_slot
            print(f"\nSlot {current_slot} - {m.start_time}")
        print(f"  Field {m.field_number}: {m.team1} vs {m.team2} (ref: {m.referee})")
    print("\nStats:")
    for team, s in sched.stats.items():
        print(f"  {team}: {s['played']} played, {s['refereed']} refereed")
