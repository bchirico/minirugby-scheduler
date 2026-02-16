# Rugby Tournament Calendar Generator

## Context
Build a tool for a kids' rugby team to generate tournament schedules. The core challenge is creating match pairings (team1 vs team2 + referee team) that satisfy multiple constraints: no time overlaps, no duplicate matches, referee availability, early-start fairness, and even referee distribution. Starting from scratch.

## Categories
Three independent categories, each treated as a separate event:
- **U8**: 10 min match + 5 min break = **15 min per slot**
- **U10**: 10 min match + 5 min break = **15 min per slot**
- **U12**: 12 min match + 5 min break = **17 min per slot**

Each category has its own teams, fields (sub-fields within one physical field), and schedule. One physical field can host all 3 categories simultaneously since each uses a small portion.

## Inputs (per category)
- Number of teams (3-8)
- Number of fields/sub-fields
- Start time
- Optional: custom team names

Match duration and break time are fixed per category (not user-configurable).

## Constraints (per category, independent)
1. Full round-robin: every pair plays exactly once → N*(N-1)/2 matches
2. Each match = team1 (plays) + team2 (plays) + referee team
3. No team can play/referee on two fields at the same time
4. No duplicate matchups
5. Every team plays within the first 2 time slots
6. Referee duties distributed evenly across teams

## Tech Stack
- **Python + Flask** (server-side rendered, no JS framework)
- **Pico CSS** via CDN for clean styling with no build step
- **WeasyPrint** for PDF (reuses HTML templates) — fallback to `fpdf2` if system deps are problematic
- **openpyxl** for Excel export

## Project Structure
```
rugby-calendar/
├── app.py              # Flask routes
├── scheduler.py        # Core scheduling algorithm
├── models.py           # Dataclasses (Match, ScheduleRequest, Schedule)
├── export.py           # PDF and Excel generation
├── templates/
│   ├── base.html       # Layout with Pico CSS
│   ├── index.html      # Input form (3 sections, one per category)
│   └── schedule.html   # Results: 3 independent schedules
├── static/
│   └── style.css       # Minimal overrides
└── requirements.txt    # flask, weasyprint, openpyxl
```

## Scheduling Algorithm (Greedy + Round-Robin ordering)

Same algorithm applied independently to each category:

1. **Generate pairs** using the circle method (standard round-robin tournament algorithm) — produces rounds where no team appears twice
2. **Greedy slot filling**: for each time slot, pack as many matches as possible (up to `min(num_fields, num_teams // 3)` simultaneous matches)
3. **Referee assignment**: for each match, pick the non-busy team with the lowest referee count
4. **Early-start check**: prioritize pairs where a team hasn't played yet in slots 0-1; warn if infeasible
5. **Time calculation**: slot N starts at `start_time + N * (match_duration + break_time)` — different per category
6. **Compute stats**: matches played and referee duties per team

## UI Design

### Input Form (`index.html`)
Three collapsible/tabbed sections — one per category (U8, U10, U12). Each section has:
- Number of teams (dropdown 3-8)
- Number of fields (dropdown 1-4)
- Start time (time input)
- Team names (dynamic fields based on team count)

Single "Generate All Schedules" button.

### Results Page (`schedule.html`)
Three sections showing each category's schedule:
- Time slot tables (time, field, team1 vs team2, referee)
- Fairness stats per category (matches played, referee duties)
- Download buttons for PDF and Excel (combined document with all 3 categories)

## Routes
| Route | Method | Description |
|---|---|---|
| `/` | GET | Input form |
| `/schedule` | POST | Generate and display all 3 schedules |
| `/download/pdf` | POST | Download PDF (all categories) |
| `/download/excel` | POST | Download Excel (one sheet per category) |

No database — schedules are stateless, regenerated from form inputs.

## Implementation Order
1. `models.py` — dataclasses (CategoryConfig added with fixed durations)
2. `scheduler.py` — core algorithm (test standalone for all 3 categories)
3. `app.py` — Flask routes + form parsing for 3 categories
4. `templates/` — base, index (tabbed form), schedule (3 sections)
5. `export.py` — PDF and Excel (one sheet per category)
6. `static/style.css` — minimal print-friendly styles
7. `requirements.txt`

## Verification
- Run `python scheduler.py` standalone to verify correct schedules for all team counts (3-8) with various field counts, for each category
- Run `python app.py` and test the web form with different configurations per category
- Verify per category: no duplicate matchups, no time conflicts, referee not playing simultaneously, all teams play by slot 2, even referee distribution
- Verify time calculations: U8/U10 slots are 15 min apart, U12 slots are 17 min apart
- Download PDF and Excel, verify all 3 categories are present and correct
