import pytest
from models import CATEGORIES, ScheduleRequest
from scheduler import generate_schedule, round_robin_order


class TestRoundRobinOrder:
    def test_generates_correct_number_of_pairs(self):
        for n in range(3, 9):
            rounds = round_robin_order(n)
            all_pairs = [p for r in rounds for p in r]
            assert len(all_pairs) == n * (n - 1) // 2

    def test_all_pairs_unique(self):
        for n in range(3, 9):
            rounds = round_robin_order(n)
            all_pairs = [p for r in rounds for p in r]
            assert len(all_pairs) == len(set(all_pairs))

    def test_pairs_are_sorted(self):
        rounds = round_robin_order(6)
        for r in rounds:
            for t1, t2 in r:
                assert t1 < t2

    def test_no_team_appears_twice_in_round(self):
        for n in range(3, 9):
            rounds = round_robin_order(n)
            for r in rounds:
                teams = [t for pair in r for t in pair]
                assert len(teams) == len(set(teams))


class TestGenerateSchedule:
    @pytest.mark.parametrize("category", ["U8", "U10", "U12"])
    @pytest.mark.parametrize("num_teams", range(3, 9))
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
    @pytest.mark.parametrize("num_teams", range(3, 9))
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
    @pytest.mark.parametrize("num_teams", range(3, 9))
    @pytest.mark.parametrize("num_fields", [1, 2, 3])
    def test_no_time_conflicts(self, category, num_teams, num_fields):
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
            teams = []
            for m in slot_matches:
                teams.extend([m.team1, m.team2, m.referee])
            assert len(teams) == len(set(teams)), f"Time conflict in slot {slot_idx}"

    @pytest.mark.parametrize("category", ["U8", "U10", "U12"])
    @pytest.mark.parametrize("num_teams", range(3, 9))
    @pytest.mark.parametrize("num_fields", [1, 2, 3])
    def test_referee_not_playing(self, category, num_teams, num_fields):
        req = ScheduleRequest(
            category=category,
            num_teams=num_teams,
            num_fields=num_fields,
            start_time="09:00",
        )
        sched = generate_schedule(req)
        for m in sched.matches:
            assert m.referee != m.team1
            assert m.referee != m.team2

    @pytest.mark.parametrize("num_teams", range(3, 9))
    def test_all_teams_play_correct_count(self, num_teams):
        req = ScheduleRequest(
            category="U8", num_teams=num_teams, num_fields=2, start_time="09:00"
        )
        sched = generate_schedule(req)
        for team, stat in sched.stats.items():
            assert stat["played"] == num_teams - 1

    def test_referee_duties_distributed_evenly(self):
        req = ScheduleRequest(
            category="U10", num_teams=6, num_fields=2, start_time="09:00"
        )
        sched = generate_schedule(req)
        ref_counts = [s["refereed"] for s in sched.stats.values()]
        assert max(ref_counts) - min(ref_counts) <= 1

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
        assert all_teams == {"Team 1", "Team 2", "Team 3", "Team 4"}

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
        assert any("starting after slot 2" in w for w in sched.warnings)

    def test_early_start_ok_with_enough_fields(self):
        req = ScheduleRequest(
            category="U8", num_teams=6, num_fields=2, start_time="09:00"
        )
        sched = generate_schedule(req)
        assert not any("starting after slot 2" in w for w in sched.warnings)


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
