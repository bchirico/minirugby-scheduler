from itertools import combinations

import pytest
from models import CATEGORIES, Match, ScheduleRequest
from scheduler import (
    _build_matches,
    _check_early_start,
    _compute_stats,
    _fill_slots,
    _ordered_pairs,
    _resolve_team_names,
    generate_schedule,
    round_robin_order,
)


class TestRoundRobinOrder:
    def test_generates_correct_number_of_pairs(self):
        for n in range(3, 11):
            rounds = round_robin_order(n)
            all_pairs = [p for r in rounds for p in r]
            assert len(all_pairs) == n * (n - 1) // 2

    def test_all_pairs_unique(self):
        for n in range(3, 11):
            rounds = round_robin_order(n)
            all_pairs = [p for r in rounds for p in r]
            assert len(all_pairs) == len(set(all_pairs))

    def test_pairs_are_sorted(self):
        rounds = round_robin_order(6)
        for r in rounds:
            for t1, t2 in r:
                assert t1 < t2

    def test_no_team_appears_twice_in_round(self):
        for n in range(3, 11):
            rounds = round_robin_order(n)
            for r in rounds:
                teams = [t for pair in r for t in pair]
                assert len(teams) == len(set(teams))


class TestGenerateSchedule:
    @pytest.mark.parametrize("category", ["U8", "U10", "U12"])
    @pytest.mark.parametrize("num_teams", range(3, 11))
    @pytest.mark.parametrize("num_fields", [1, 2, 3])
    def test_correct_number_of_matches(self, category, num_teams, num_fields):
        req = ScheduleRequest(
            category=category,
            num_teams=num_teams,
            num_fields=num_fields,
            start_time="09:00",
        )
        sched = generate_schedule(req)
        assert len(sched.matches) == num_teams * (num_teams - 1) // 2

    @pytest.mark.parametrize("category", ["U8", "U10", "U12"])
    @pytest.mark.parametrize("num_teams", range(3, 11))
    @pytest.mark.parametrize("num_fields", [1, 2, 3])
    def test_no_duplicate_matchups(self, category, num_teams, num_fields):
        req = ScheduleRequest(
            category=category,
            num_teams=num_teams,
            num_fields=num_fields,
            start_time="09:00",
        )
        sched = generate_schedule(req)
        pairs = set()
        for m in sched.matches:
            pair = tuple(sorted([m.team1, m.team2]))
            assert pair not in pairs, f"Duplicate matchup: {pair}"
            pairs.add(pair)

    @pytest.mark.parametrize("category", ["U8", "U10", "U12"])
    @pytest.mark.parametrize("num_teams", range(3, 11))
    @pytest.mark.parametrize("num_fields", [1, 2, 3])
    def test_no_playing_conflicts(self, category, num_teams, num_fields):
        req = ScheduleRequest(
            category=category,
            num_teams=num_teams,
            num_fields=num_fields,
            start_time="09:00",
        )
        sched = generate_schedule(req)
        slots = {}
        for m in sched.matches:
            slots.setdefault(m.time_slot, []).append(m)
        for slot_idx, slot_matches in slots.items():
            players = []
            for m in slot_matches:
                players.extend([m.team1, m.team2])
            assert len(players) == len(set(players)), (
                f"Playing conflict in slot {slot_idx}"
            )

    @pytest.mark.parametrize("category", ["U8", "U10", "U12"])
    @pytest.mark.parametrize("num_teams", range(3, 11))
    @pytest.mark.parametrize("num_fields", [1, 2, 3])
    def test_no_time_conflicts_dedicated(self, category, num_teams, num_fields):
        req = ScheduleRequest(
            category=category,
            num_teams=num_teams,
            num_fields=num_fields,
            start_time="09:00",
            dedicated_referees=True,
        )
        sched = generate_schedule(req)
        slots = {}
        for m in sched.matches:
            slots.setdefault(m.time_slot, []).append(m)
        for slot_idx, slot_matches in slots.items():
            teams = []
            for m in slot_matches:
                teams.extend([m.team1, m.team2, m.referee])
            assert len(teams) == len(set(teams)), f"Time conflict in slot {slot_idx}"

    @pytest.mark.parametrize("category", ["U8", "U10", "U12"])
    @pytest.mark.parametrize("num_teams", range(3, 11))
    @pytest.mark.parametrize("num_fields", [1, 2, 3])
    def test_referee_not_playing_dedicated(self, category, num_teams, num_fields):
        req = ScheduleRequest(
            category=category,
            num_teams=num_teams,
            num_fields=num_fields,
            start_time="09:00",
            dedicated_referees=True,
        )
        sched = generate_schedule(req)
        for m in sched.matches:
            assert m.referee != m.team1
            assert m.referee != m.team2

    @pytest.mark.parametrize("num_teams", range(3, 11))
    def test_all_teams_play_correct_count(self, num_teams):
        req = ScheduleRequest(
            category="U8", num_teams=num_teams, num_fields=2, start_time="09:00"
        )
        sched = generate_schedule(req)
        for team, stat in sched.stats.items():
            assert stat["played"] == num_teams - 1

    @pytest.mark.parametrize("num_teams", range(3, 11))
    @pytest.mark.parametrize("num_fields", [1, 2, 3])
    @pytest.mark.parametrize("dedicated_referees", [True, False])
    def test_referee_duties_distributed_evenly(
        self, num_teams, num_fields, dedicated_referees
    ):
        req = ScheduleRequest(
            category="U10",
            num_teams=num_teams,
            num_fields=num_fields,
            start_time="09:00",
            dedicated_referees=dedicated_referees,
        )
        sched = generate_schedule(req)
        if not sched.matches:
            return
        ref_counts = [s["refereed"] for s in sched.stats.values()]
        assert max(ref_counts) - min(ref_counts) <= 1, (
            f"{num_teams}t {num_fields}f ded={dedicated_referees}: "
            f"ref counts = {dict(zip(sched.stats.keys(), ref_counts))}"
        )

    def test_custom_team_names(self):
        names = ["Lions", "Tigers", "Bears", "Eagles"]
        req = ScheduleRequest(
            category="U8",
            num_teams=4,
            num_fields=1,
            start_time="09:00",
            team_names=names,
        )
        sched = generate_schedule(req)
        all_teams = set()
        for m in sched.matches:
            all_teams.update([m.team1, m.team2, m.referee])
        assert all_teams == set(names)

    def test_default_team_names(self):
        req = ScheduleRequest(
            category="U8", num_teams=4, num_fields=1, start_time="09:00"
        )
        sched = generate_schedule(req)
        all_teams = set()
        for m in sched.matches:
            all_teams.update([m.team1, m.team2])
        assert all_teams == {"Squadra 1", "Squadra 2", "Squadra 3", "Squadra 4"}

    def test_time_slots_u8(self):
        req = ScheduleRequest(
            category="U8", num_teams=3, num_fields=1, start_time="09:00"
        )
        sched = generate_schedule(req)
        times = [m.start_time for m in sched.matches]
        assert times == ["09:00", "09:15", "09:30"]  # 10 + 5 = 15 min

    def test_time_slots_u12(self):
        req = ScheduleRequest(
            category="U12", num_teams=3, num_fields=1, start_time="10:00"
        )
        sched = generate_schedule(req)
        times = [m.start_time for m in sched.matches]
        assert times == ["10:00", "10:17", "10:34"]  # 12 + 5 = 17 min

    def test_multiple_fields_reduce_slots(self):
        req_1f = ScheduleRequest(
            category="U10", num_teams=6, num_fields=1, start_time="09:00"
        )
        req_2f = ScheduleRequest(
            category="U10", num_teams=6, num_fields=2, start_time="09:00"
        )
        sched_1f = generate_schedule(req_1f)
        sched_2f = generate_schedule(req_2f)
        slots_1f = len(set(m.time_slot for m in sched_1f.matches))
        slots_2f = len(set(m.time_slot for m in sched_2f.matches))
        assert slots_2f < slots_1f

    def test_category_preserved(self):
        req = ScheduleRequest(
            category="U12", num_teams=4, num_fields=1, start_time="09:00"
        )
        sched = generate_schedule(req)
        assert sched.category == "U12"

    def test_early_start_warning_with_many_teams_one_field(self):
        req = ScheduleRequest(
            category="U8", num_teams=8, num_fields=1, start_time="09:00"
        )
        sched = generate_schedule(req)
        assert any("iniziano dopo lo slot 2" in w for w in sched.warnings)

    def test_early_start_ok_with_enough_fields(self):
        req = ScheduleRequest(
            category="U8", num_teams=6, num_fields=2, start_time="09:00"
        )
        sched = generate_schedule(req)
        assert not any("iniziano dopo lo slot 2" in w for w in sched.warnings)

    def test_time_overrun_warning(self):
        # 6 teams: each plays 5 matches, 5*10=50 > 40
        req = ScheduleRequest(
            category="U8",
            num_teams=6,
            num_fields=2,
            start_time="09:00",
            total_game_time=40,
            match_duration=10,
            break_duration=5,
        )
        sched = generate_schedule(req)
        assert sched.time_overrun_warning is not None
        assert "supera il limite" in sched.time_overrun_warning

    def test_no_time_overrun_when_within_budget(self):
        # 3 teams: each plays 2 matches, 2*10=20 <= 45
        req = ScheduleRequest(
            category="U8",
            num_teams=3,
            num_fields=1,
            start_time="09:00",
            total_game_time=45,
            match_duration=10,
            break_duration=5,
        )
        sched = generate_schedule(req)
        assert sched.time_overrun_warning is None

    def test_custom_match_duration_used(self):
        req = ScheduleRequest(
            category="U8",
            num_teams=3,
            num_fields=1,
            start_time="09:00",
            match_duration=8,
            break_duration=4,
        )
        sched = generate_schedule(req)
        # 3 teams, 1 field: 3 matches in 3 slots, slot_duration = 8+4 = 12
        assert sched.matches[0].start_time == "09:00"
        assert sched.matches[1].start_time == "09:12"
        assert sched.matches[2].start_time == "09:24"

    def test_non_dedicated_uses_fewer_slots(self):
        req_ded = ScheduleRequest(
            category="U10",
            num_teams=6,
            num_fields=3,
            start_time="09:00",
            dedicated_referees=True,
        )
        req_non = ScheduleRequest(
            category="U10",
            num_teams=6,
            num_fields=3,
            start_time="09:00",
            dedicated_referees=False,
        )
        sched_ded = generate_schedule(req_ded)
        sched_non = generate_schedule(req_non)
        slots_ded = len(set(m.time_slot for m in sched_ded.matches))
        slots_non = len(set(m.time_slot for m in sched_non.matches))
        assert slots_non < slots_ded


class TestResolveTeamNames:
    def test_uses_custom_names_when_correct_length(self):
        req = ScheduleRequest(
            category="U8",
            num_teams=3,
            num_fields=1,
            start_time="09:00",
            team_names=["A", "B", "C"],
        )
        assert _resolve_team_names(req) == ["A", "B", "C"]

    def test_falls_back_to_defaults_when_wrong_length(self):
        req = ScheduleRequest(
            category="U8",
            num_teams=3,
            num_fields=1,
            start_time="09:00",
            team_names=["A", "B"],
        )
        assert _resolve_team_names(req) == ["Squadra 1", "Squadra 2", "Squadra 3"]

    def test_falls_back_to_defaults_when_empty(self):
        req = ScheduleRequest(
            category="U8", num_teams=3, num_fields=1, start_time="09:00"
        )
        assert _resolve_team_names(req) == ["Squadra 1", "Squadra 2", "Squadra 3"]


class TestOrderedPairs:
    def test_covers_all_pairs(self):
        for n in range(3, 11):
            pairs = _ordered_pairs(n)
            assert set(pairs) == set(combinations(range(n), 2))

    def test_preserves_round_robin_order(self):
        pairs = _ordered_pairs(4)
        rounds = round_robin_order(4)
        expected = [pair for r in rounds for pair in r]
        assert pairs == expected


class TestFillSlots:
    def test_schedules_all_pairs(self):
        slots, _, warnings = _fill_slots(4, max_simultaneous=1, dedicated_referees=True)
        scheduled = {(t1, t2) for slot in slots for t1, t2, _, _ in slot}
        assert scheduled == set(combinations(range(4), 2))
        assert not warnings

    def test_respects_max_simultaneous(self):
        slots, _, _ = _fill_slots(6, max_simultaneous=2, dedicated_referees=True)
        for slot in slots:
            assert len(slot) <= 2

    def test_no_team_appears_twice_in_slot_dedicated(self):
        slots, _, _ = _fill_slots(6, max_simultaneous=2, dedicated_referees=True)
        for slot in slots:
            teams = []
            for t1, t2, ref, _ in slot:
                teams.extend([t1, t2, ref])
            assert len(teams) == len(set(teams))

    def test_referee_counts_balanced(self):
        _, referee_counts, _ = _fill_slots(
            6, max_simultaneous=2, dedicated_referees=True
        )
        counts = list(referee_counts.values())
        assert max(counts) - min(counts) <= 1

    def test_non_dedicated_allows_more_simultaneous(self):
        slots, _, warnings = _fill_slots(
            6, max_simultaneous=3, dedicated_referees=False
        )
        assert not warnings
        assert any(len(slot) == 3 for slot in slots)

    def test_non_dedicated_own_team_referee_fallback(self):
        """With 4 teams and 2 fields, all play and all referee — one must ref own match."""
        slots, _, warnings = _fill_slots(
            4, max_simultaneous=2, dedicated_referees=False
        )
        assert not warnings
        scheduled = {(t1, t2) for slot in slots for t1, t2, _, _ in slot}
        assert scheduled == set(combinations(range(4), 2))

    def test_full_slots_before_partial(self):
        """Full slots should come before partial slots."""
        slots, _, _ = _fill_slots(8, max_simultaneous=3, dedicated_referees=False)
        sizes = [len(s) for s in slots]
        # All full slots come before any partial slot
        full_done = False
        for s in sizes:
            if s < 3:
                full_done = True
            elif full_done:
                assert False, f"Full slot after partial: {sizes}"

    def test_non_dedicated_no_playing_conflict(self):
        slots, _, _ = _fill_slots(6, max_simultaneous=3, dedicated_referees=False)
        for slot in slots:
            players = []
            for t1, t2, _, _ in slot:
                players.extend([t1, t2])
            assert len(players) == len(set(players))


class TestCheckEarlyStart:
    def test_no_warnings_when_all_play_early(self):
        # 3 teams, 1 match per slot: everyone plays by slot 1
        slots = [
            [(0, 1, 2, 1)],
            [(0, 2, 1, 1)],
            [(1, 2, 0, 1)],
        ]
        warnings = _check_early_start(3, ["A", "B", "C"], slots)
        assert not warnings

    def test_warns_on_late_starter(self):
        # Team 2 doesn't play until slot 2 (0-indexed)
        slots = [
            [(0, 1, 2, 1)],
            [(0, 1, 2, 1)],
            [(0, 2, 1, 1)],
        ]
        warnings = _check_early_start(3, ["A", "B", "C"], slots)
        assert any("iniziano dopo lo slot 2" in w for w in warnings)


class TestBuildMatches:
    def test_assigns_correct_times(self):
        slots = [
            [(0, 1, 2, 1)],
            [(0, 2, 1, 1)],
        ]
        matches = _build_matches(slots, ["A", "B", "C"], "09:00", 15)
        assert matches[0].start_time == "09:00"
        assert matches[1].start_time == "09:15"

    def test_assigns_team_names(self):
        slots = [[(0, 1, 2, 1)]]
        matches = _build_matches(slots, ["A", "B", "C"], "09:00", 15)
        assert matches[0].team1 == "A"
        assert matches[0].team2 == "B"
        assert matches[0].referee == "C"

    def test_match_numbers_sequential(self):
        slots = [[(0, 1, 2, 1), (3, 4, 5, 2)], [(0, 2, 1, 1)]]
        names = ["A", "B", "C", "D", "E", "F"]
        matches = _build_matches(slots, names, "09:00", 15)
        assert [m.match_number for m in matches] == [1, 2, 3]


class TestComputeStats:
    def test_counts_played_and_refereed(self):
        matches = [
            Match(1, "A", "B", "C", 1, 0, "09:00"),
            Match(2, "A", "C", "B", 1, 1, "09:15"),
            Match(3, "B", "C", "A", 1, 2, "09:30"),
        ]
        referee_counts = {0: 1, 1: 1, 2: 1}
        stats = _compute_stats(3, ["A", "B", "C"], matches, referee_counts, 15)
        for name in ["A", "B", "C"]:
            assert stats[name]["played"] == 2
            assert stats[name]["refereed"] == 1

    def test_max_wait(self):
        matches = [
            Match(1, "A", "B", "C", 1, 0, "09:00"),
            Match(2, "A", "C", "B", 1, 1, "09:15"),
            Match(3, "B", "C", "A", 1, 3, "09:45"),
        ]
        referee_counts = {0: 1, 1: 1, 2: 1}
        # slot_duration=15, break_duration=5
        # max_wait = (gap - 1) * slot_duration + break_duration
        stats = _compute_stats(
            3, ["A", "B", "C"], matches, referee_counts, 15, break_duration=5
        )
        # A plays slots 0,1 -> gap 1 -> (1-1)*15 + 5 = 5 min
        assert stats["A"]["max_wait"] == 5
        # B plays slots 0,3 -> gap 3 -> (3-1)*15 + 5 = 35 min
        assert stats["B"]["max_wait"] == 35
        # C plays slots 1,3 -> gap 2 -> (2-1)*15 + 5 = 20 min
        assert stats["C"]["max_wait"] == 20


class TestLunchBreak:
    def test_morning_slots_half_split(self):
        """With split='half' and 8 total slots, morning_slots = ceil(8/2) = 4."""
        req = ScheduleRequest(
            category="U10",
            num_teams=6,
            num_fields=2,
            start_time="09:00",
            lunch_break=60,
            split_ratio="half",
        )
        sched = generate_schedule(req)
        total_slots = len(set(m.time_slot for m in sched.matches))
        import math

        assert sched.morning_slots == math.ceil(total_slots / 2)

    def test_morning_slots_two_thirds_split(self):
        """With split='two_thirds', morning_slots = ceil(total * 2/3)."""
        req = ScheduleRequest(
            category="U10",
            num_teams=6,
            num_fields=2,
            start_time="09:00",
            lunch_break=60,
            split_ratio="two_thirds",
        )
        sched = generate_schedule(req)
        total_slots = len(set(m.time_slot for m in sched.matches))
        import math

        assert sched.morning_slots == math.ceil(total_slots * 2 / 3)

    def test_no_split_when_lunch_break_zero(self):
        """Without lunch_break, morning_slots stays 0."""
        req = ScheduleRequest(
            category="U10",
            num_teams=6,
            num_fields=2,
            start_time="09:00",
            lunch_break=0,
            split_ratio="half",
        )
        sched = generate_schedule(req)
        assert sched.morning_slots == 0

    def test_afternoon_slots_shifted(self):
        """Afternoon start times are offset by (lunch_break - break_duration)."""
        # U8: slot_duration=15, match=10, break=5
        # 3 teams, 1 field -> 3 slots. With half split: morning_slots=2, afternoon=1
        req = ScheduleRequest(
            category="U8",
            num_teams=3,
            num_fields=1,
            start_time="09:00",
            match_duration=10,
            break_duration=5,
            lunch_break=60,
            split_ratio="half",
        )
        sched = generate_schedule(req)
        # morning slot 0: 09:00, morning slot 1: 09:15
        # afternoon slot 2 (without lunch): 09:30
        # afternoon slot 2 (with lunch 60, offset=60-5=55): 09:30 + 55 = 10:25
        afternoon_matches = [
            m for m in sched.matches if m.time_slot >= sched.morning_slots
        ]
        assert afternoon_matches[0].start_time == "10:25"

    def test_lunch_break_replaces_ordinary_break(self):
        """The gap between last morning and first afternoon equals lunch_break, not break_duration."""
        req = ScheduleRequest(
            category="U8",
            num_teams=3,
            num_fields=1,
            start_time="09:00",
            match_duration=10,
            break_duration=5,
            lunch_break=30,
            split_ratio="half",
        )
        sched = generate_schedule(req)
        last_morning = max(
            (m for m in sched.matches if m.time_slot < sched.morning_slots),
            key=lambda m: m.time_slot,
        )
        first_afternoon = min(
            (m for m in sched.matches if m.time_slot >= sched.morning_slots),
            key=lambda m: m.time_slot,
        )
        from datetime import datetime

        t_last = datetime.strptime(last_morning.start_time, "%H:%M")
        t_first = datetime.strptime(first_afternoon.start_time, "%H:%M")
        gap = int((t_first - t_last).total_seconds() / 60)
        # gap = match_duration + lunch_break = 10 + 30 = 40 min
        assert gap == 10 + 30


class TestHalfTimeInterval:
    def test_interval_increases_slot_duration(self):
        """half_time_interval adds to slot duration (affects match start times)."""
        req = ScheduleRequest(
            category="U12",
            num_teams=3,
            num_fields=1,
            start_time="09:00",
            match_duration=12,
            break_duration=5,
            half_time_interval=2,
        )
        sched = generate_schedule(req)
        # slot_duration = 12 + 2 + 5 = 19 min
        times = [m.start_time for m in sched.matches]
        assert times == ["09:00", "09:19", "09:38"]

    def test_interval_not_counted_as_play_time(self):
        """half_time_interval is excluded from the time-overrun budget check."""
        # 3 teams: 2 matches each, match_duration=12 -> actual play = 24 min
        # budget = 20 min -> overrun (24 > 20), interval should not affect check
        req = ScheduleRequest(
            category="U12",
            num_teams=3,
            num_fields=1,
            start_time="09:00",
            match_duration=12,
            break_duration=5,
            half_time_interval=3,
            total_game_time=20,
        )
        sched = generate_schedule(req)
        assert sched.time_overrun_warning is not None
        assert "supera il limite" in sched.time_overrun_warning

    def test_interval_zero_does_not_change_slot_duration(self):
        """With half_time_interval=0, slot duration matches the base U12 default."""
        req = ScheduleRequest(
            category="U12", num_teams=3, num_fields=1, start_time="10:00"
        )
        sched = generate_schedule(req)
        times = [m.start_time for m in sched.matches]
        assert times == ["10:00", "10:17", "10:34"]  # 12 + 5 = 17 min

    def test_interval_stored_on_schedule(self):
        req = ScheduleRequest(
            category="U12",
            num_teams=4,
            num_fields=1,
            start_time="09:00",
            half_time_interval=2,
        )
        sched = generate_schedule(req)
        assert sched.half_time_interval == 2

    def test_interval_default_is_zero(self):
        req = ScheduleRequest(
            category="U12", num_teams=4, num_fields=1, start_time="09:00"
        )
        sched = generate_schedule(req)
        assert sched.half_time_interval == 0


class TestModels:
    def test_slot_duration(self):
        assert CATEGORIES["U8"].slot_duration == 15
        assert CATEGORIES["U10"].slot_duration == 15
        assert CATEGORIES["U12"].slot_duration == 17

    def test_category_field_dimensions(self):
        assert CATEGORIES["U8"].field_width == "17-20m"
        assert CATEGORIES["U8"].field_length == "45m"
        assert CATEGORIES["U10"].field_length == "60-70m"
        assert CATEGORIES["U12"].field_width == "40-45m"
