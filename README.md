# Rugby Tournament Calendar Generator

Generate round-robin tournament schedules for kids' rugby with automatic matchup creation, referee assignment, and fair scheduling.

## Features

- **Three categories**: U8 (10+5 min), U10 (10+5 min), U12 (12+5 min) — each scheduled independently
- **Full round-robin**: every pair of teams plays exactly once
- **Referee assignment**: a third team referees each match, duties distributed evenly
- **Constraint satisfaction**: no time conflicts, no duplicate matchups, early-start fairness
- **Multiple fields**: parallel matches on sub-fields
- **Export**: PDF and Excel downloads

## Setup

```bash
pip install -r requirements.txt
python3 app.py
```

Open http://localhost:5050

## How it works

For each category, select the number of teams (3–8), fields, start time, and optionally name the teams. The scheduler uses a greedy algorithm with round-robin ordering (circle method) to fill time slots, assign referees fairly, and ensure every team plays as early as possible.

## Project structure

```
app.py          — Flask routes
scheduler.py    — Scheduling algorithm
models.py       — Data classes
export.py       — PDF and Excel generation
templates/      — HTML templates (Pico CSS)
static/         — Stylesheet
```
