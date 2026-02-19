from dataclasses import dataclass, field
from typing import Optional


TOTAL_GAME_TIMES = {
    "U6": {"half": 30, "full": 45},
    "U8": {"half": 45, "full": 54},
    "U10": {"half": 50, "full": 60},
    "U12": {"half": 60, "full": 70},
}

RECOMMENDED_MATCH_TIMES = {
    "U6": 7,
    "U8": 10,
    "U10": 10,
    "U12": 12,
}

# U6 field dimensions vary by match format (players per side)
U6_FIELD_FORMATS = {
    3: {"field_width": "5m",  "field_length": "15m", "field_width_max": 5,  "field_length_max": 15, "meta": 2},
    4: {"field_width": "10m", "field_length": "22m", "field_width_max": 10, "field_length_max": 22, "meta": 2},
    5: {"field_width": "15m", "field_length": "22m", "field_width_max": 15, "field_length_max": 22, "meta": 2},
}


@dataclass
class CategoryConfig:
    name: str  # "U6", "U8", "U10", "U12"
    match_duration: int  # minutes
    break_duration: int  # minutes
    field_width: str  # e.g. "17-20m"
    field_length: str  # e.g. "45m"
    field_width_max: int  # max width in meters (for drawing scale)
    field_length_max: int  # max length in meters (for drawing scale)
    meta: int = 5  # in-goal area in meters

    @property
    def slot_duration(self) -> int:
        return self.match_duration + self.break_duration


CATEGORIES = {
    "U6": CategoryConfig(
        "U6",
        match_duration=7,
        break_duration=5,
        # Default to 4v4 dimensions; actual dimensions resolved via U6_FIELD_FORMATS
        field_width="10m",
        field_length="22m",
        field_width_max=10,
        field_length_max=22,
        meta=2,
    ),
    "U8": CategoryConfig(
        "U8",
        match_duration=10,
        break_duration=5,
        field_width="17-20m",
        field_length="45m",
        field_width_max=20,
        field_length_max=45,
    ),
    "U10": CategoryConfig(
        "U10",
        match_duration=10,
        break_duration=5,
        field_width="30m",
        field_length="60-70m",
        field_width_max=30,
        field_length_max=70,
    ),
    "U12": CategoryConfig(
        "U12",
        match_duration=12,
        break_duration=5,
        field_width="40-45m",
        field_length="55-70m",
        field_width_max=45,
        field_length_max=70,
    ),
}


@dataclass
class Match:
    match_number: int
    team1: str
    team2: str
    referee: str
    field_number: int  # 1-indexed
    time_slot: int  # 0-indexed
    start_time: str  # "HH:MM"


@dataclass
class ScheduleRequest:
    category: str  # "U6", "U8", "U10", "U12"
    num_teams: int
    num_fields: int
    start_time: str  # "HH:MM"
    total_game_time: int = 0  # total playing minutes budget
    match_duration: int = 0  # minutes per match
    break_duration: int = 0  # minutes per break
    team_names: list[str] = field(default_factory=list)
    dedicated_referees: bool = False
    no_referee: bool = False  # if True, referee column is omitted entirely
    half_time_interval: int = 0  # minutes of half-time break (U12 only)

    def get_config(self) -> CategoryConfig:
        return CATEGORIES[self.category]


@dataclass
class Schedule:
    category: str
    matches: list[Match]
    warnings: list[str]
    stats: dict  # {team_name: {"played": int, "refereed": int}}
    match_duration: int = 0
    break_duration: int = 0
    no_referee: bool = False
    half_time_interval: int = 0  # minutes of half-time break (U12 only)
    time_overrun_warning: Optional[str] = None

    @property
    def resting_per_slot(self) -> dict[int, list[str]]:
        """Returns {time_slot: [teams not playing in that slot]}."""
        all_teams = set(self.stats.keys())
        playing_per_slot: dict[int, set[str]] = {}
        for m in self.matches:
            playing_per_slot.setdefault(m.time_slot, set()).update([m.team1, m.team2])
        return {
            slot: sorted(all_teams - playing)
            for slot, playing in playing_per_slot.items()
        }
