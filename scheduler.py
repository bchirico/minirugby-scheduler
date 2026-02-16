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


def _resolve_team_names(request: ScheduleRequest) -> list[str]:
    n = request.num_teams
    if request.team_names and len(request.team_names) == n:
        return request.team_names
    return [f"Squadra {i + 1}" for i in range(n)]


def _ordered_pairs(n: int) -> list[tuple[int, int]]:
    all_pairs = set(combinations(range(n), 2))
    rounds = round_robin_order(n)
    ordered = [pair for r in rounds for pair in r]
    assert set(ordered) == all_pairs
    return ordered


def _fill_slots(
    n: int,
    ordered_pairs: list[tuple[int, int]],
    max_simultaneous: int,
    dedicated_referees: bool = True,
) -> tuple[list[list[tuple[int, int, int, int]]], dict[int, int], list[str]]:
    unscheduled = list(ordered_pairs)
    slots: list[list[tuple[int, int, int, int]]] = []
    referee_counts = {i: 0 for i in range(n)}
    has_played: set[int] = set()
    warnings: list[str] = []

    while unscheduled:
        slot_index = len(slots)
        playing_teams: set[int] = set()

        if slot_index < 2:
            unscheduled.sort(
                key=lambda p: (
                    p[0] in has_played and p[1] in has_played,
                    min(referee_counts[p[0]], referee_counts[p[1]]),
                )
            )

        # Phase 1: schedule matches (playing pairs only)
        scheduled_this_slot: list[tuple[int, int]] = []
        for pair in unscheduled:
            if len(scheduled_this_slot) >= max_simultaneous:
                break
            t1, t2 = pair
            if t1 in playing_teams or t2 in playing_teams:
                continue
            scheduled_this_slot.append(pair)
            playing_teams.update({t1, t2})

        # Phase 2: assign referees
        current_slot: list[tuple[int, int, int, int]] = []
        refereeing_teams: set[int] = set()
        for t1, t2 in scheduled_this_slot:
            # Prefer resting teams (not playing, not already refereeing)
            resting = [
                t
                for t in range(n)
                if t not in playing_teams
                and t not in refereeing_teams
                and t != t1
                and t != t2
            ]
            if resting:
                referee = min(resting, key=lambda t: referee_counts[t])
            elif not dedicated_referees:
                # One of the two playing teams referees their own match
                own_candidates = [t for t in (t1, t2) if t not in refereeing_teams]
                if own_candidates:
                    referee = min(own_candidates, key=lambda t: referee_counts[t])
                else:
                    continue
            else:
                continue

            field_num = len(current_slot) + 1
            current_slot.append((t1, t2, referee, field_num))
            refereeing_teams.add(referee)
            referee_counts[referee] += 1
            has_played.update({t1, t2})

        for t1, t2, _, _ in current_slot:
            unscheduled.remove((t1, t2))

        if not current_slot:
            warnings.append(
                "Non è stato possibile programmare tutte le partite. Alcune partite potrebbero mancare."
            )
            break

        slots.append(current_slot)

    # Push partial slots to the end so full slots come first
    slots.sort(key=lambda s: len(s), reverse=True)

    return slots, referee_counts, warnings


def _check_early_start(
    n: int,
    team_names: list[str],
    slots: list[list[tuple[int, int, int, int]]],
) -> list[str]:
    warnings = []

    first_play_slot: dict[int, int | None] = {i: None for i in range(n)}
    for slot_idx, slot in enumerate(slots):
        for t1, t2, _ref, _field in slot:
            if first_play_slot[t1] is None:
                first_play_slot[t1] = slot_idx
            if first_play_slot[t2] is None:
                first_play_slot[t2] = slot_idx

    never_played = [team_names[t] for t in range(n) if first_play_slot[t] is None]
    if never_played:
        warnings.append(
            f"Squadre che non giocano nei primi 2 slot: {', '.join(never_played)}"
        )

    late_starters = [
        team_names[t]
        for t in range(n)
        if first_play_slot[t] is not None and first_play_slot[t] > 1
    ]
    if late_starters:
        warnings.append(
            f"Squadre che iniziano dopo lo slot 2: {', '.join(late_starters)}"
        )

    return warnings


def _build_matches(
    slots: list[list[tuple[int, int, int, int]]],
    team_names: list[str],
    start_time: str,
    slot_duration: int,
) -> list[Match]:
    base_time = datetime.strptime(start_time, "%H:%M")
    matches = []
    match_num = 1

    for slot_idx, slot in enumerate(slots):
        slot_time = base_time + timedelta(minutes=slot_idx * slot_duration)
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

    return matches


def _compute_stats(
    n: int, team_names: list[str], matches: list[Match], referee_counts: dict[int, int]
) -> dict:
    stats = {}
    for i in range(n):
        name = team_names[i]
        played = sum(1 for m in matches if m.team1 == name or m.team2 == name)
        stats[name] = {"played": played, "refereed": referee_counts[i]}
    return stats


def generate_schedule(request: ScheduleRequest) -> Schedule:
    n = request.num_teams
    config = request.get_config()
    team_names = _resolve_team_names(request)

    if request.dedicated_referees:
        max_simultaneous = max(1, min(request.num_fields, n // 3))
    else:
        max_simultaneous = max(1, min(request.num_fields, n // 2))
    ordered_pairs = _ordered_pairs(n)

    slots, referee_counts, warnings = _fill_slots(
        n, ordered_pairs, max_simultaneous, request.dedicated_referees
    )
    warnings += _check_early_start(n, team_names, slots)
    matches = _build_matches(
        slots, team_names, request.start_time, config.slot_duration
    )
    stats = _compute_stats(n, team_names, matches, referee_counts)

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

                # Verify no playing conflicts (a team can't play two matches at once)
                for slot_idx in range(max(m.time_slot for m in sched.matches) + 1):
                    slot_matches = [m for m in sched.matches if m.time_slot == slot_idx]
                    players_in_slot = []
                    for m in slot_matches:
                        players_in_slot.extend([m.team1, m.team2])
                    assert len(players_in_slot) == len(set(players_in_slot)), (
                        f"Playing conflict in {category} {num_teams}t {num_fields}f slot {slot_idx}"
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
