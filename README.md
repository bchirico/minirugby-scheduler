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
make install
make run
```

Open http://localhost:5050

## Development

```bash
make test      # Run tests
make lint      # Run linter (ruff check)
make format    # Format code (ruff format)
make all       # Format + lint + test
```

## How it works

For each category, select the number of teams (3–8), fields, start time, and optionally name the teams. The scheduler uses a greedy algorithm with round-robin ordering (circle method) to fill time slots, assign referees fairly, and ensure every team plays as early as possible.

## Deploy to Render

The app is configured for [Render](https://render.com) free tier. Deploys are triggered automatically when a GitHub release is published.

### First-time setup

1. Push the repo to GitHub
2. Sign up on [render.com](https://render.com) with your GitHub account
3. Create a **New > Web Service** and connect the repo — Render will auto-detect `render.yaml`
4. In Render dashboard > your service > **Settings** > set **Auto-Deploy** to **No**
5. In Render dashboard > your service > **Settings** > copy the **Deploy Hook URL**
6. In GitHub > repo > **Settings > Secrets and variables > Actions** > add a secret called `RENDER_DEPLOY_HOOK_URL` with the hook URL

### Deploying

Create a release on GitHub — the GitHub Action (`.github/workflows/deploy.yml`) will trigger a Render redeploy automatically.

## Project structure

```
app.py          — Flask routes
scheduler.py    — Scheduling algorithm
models.py       — Data classes
export.py       — PDF and Excel generation
templates/      — HTML templates (Pico CSS)
static/         — Stylesheet
```
