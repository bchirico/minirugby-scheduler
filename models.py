from dataclasses import dataclass, field


@dataclass
class CategoryConfig:
    name: str  # "U8", "U10", "U12"
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
    "U8": CategoryConfig("U8", match_duration=10, break_duration=5,
                          field_width="17-20m", field_length="45m",
                          field_width_max=20, field_length_max=45),
    "U10": CategoryConfig("U10", match_duration=10, break_duration=5,
                           field_width="30m", field_length="55m",
                           field_width_max=30, field_length_max=55),
    "U12": CategoryConfig("U12", match_duration=12, break_duration=5,
                           field_width="40-45m", field_length="55-70m",
                           field_width_max=45, field_length_max=70),
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
    category: str  # "U8", "U10", "U12"
    num_teams: int
    num_fields: int
    start_time: str  # "HH:MM"
    team_names: list[str] = field(default_factory=list)

    def get_config(self) -> CategoryConfig:
        return CATEGORIES[self.category]


@dataclass
class Schedule:
    category: str
    matches: list[Match]
    warnings: list[str]
    stats: dict  # {team_name: {"played": int, "refereed": int}}
