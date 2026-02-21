from datetime import datetime
from io import BytesIO

from flask import Flask, jsonify, render_template, request, send_file

from models import (
    CATEGORIES,
    TOTAL_GAME_TIMES,
    RECOMMENDED_MATCH_TIMES,
    ScheduleRequest,
    Schedule,
)
from scheduler import generate_schedule
from export import schedule_to_pdf, schedule_to_excel
from sessions import load_sessions, save_session

app = Flask(__name__)

CATEGORY_ORDER = ["U6", "U8", "U10", "U12"]


def parse_form(form) -> list[ScheduleRequest]:
    """Parse form data into a list of ScheduleRequests, one per active category."""
    requests = []
    for cat in CATEGORY_ORDER:
        enabled = form.get(f"{cat}_enabled")
        if not enabled:
            continue

        num_teams = int(form.get(f"{cat}_num_teams", 4))
        num_fields = int(form.get(f"{cat}_num_fields", 1))
        start_time = form.get(f"{cat}_start_time", "09:00")

        config = CATEGORIES[cat]
        is_full_day = bool(form.get(f"{cat}_full_day"))
        day_key = "full" if is_full_day else "half"
        default_total = TOTAL_GAME_TIMES[cat][day_key]
        total_game_time = int(form.get(f"{cat}_total_game_time", default_total))
        match_duration = int(form.get(f"{cat}_match_duration", config.match_duration))
        break_duration = int(form.get(f"{cat}_break_duration", config.break_duration))

        team_names = []
        for i in range(1, num_teams + 1):
            name = form.get(f"{cat}_team_{i}", "").strip()
            team_names.append(name if name else f"Squadra {i}")

        no_referee = bool(form.get(f"{cat}_no_referee"))
        half_time_interval = int(form.get(f"{cat}_half_time_interval", 0) or 0)
        lunch_break = int(form.get(f"{cat}_lunch_break", 0) or 0)
        split_ratio = form.get(f"{cat}_split_ratio", "half")
        requests.append(
            ScheduleRequest(
                category=cat,
                num_teams=num_teams,
                num_fields=num_fields,
                start_time=start_time,
                total_game_time=total_game_time,
                match_duration=match_duration,
                break_duration=break_duration,
                team_names=team_names,
                no_referee=no_referee,
                half_time_interval=half_time_interval,
                lunch_break=lunch_break,
                split_ratio=split_ratio,
            )
        )
    return requests


def generate_all(form) -> list[Schedule]:
    reqs = parse_form(form)
    return [generate_schedule(req) for req in reqs]


@app.route("/")
def index():
    return render_template(
        "index.html",
        categories=CATEGORIES,
        category_order=CATEGORY_ORDER,
        total_game_times=TOTAL_GAME_TIMES,
        recommended_match_times=RECOMMENDED_MATCH_TIMES,
        sessions=load_sessions(),
    )


@app.route("/save-session", methods=["POST"])
def save_session_route():
    data = request.get_json(silent=True) or {}
    label = str(data.get("label", "")).strip()
    form_data = data.get("form_data", {})
    if not label:
        event_name = form_data.get("event_name", "").strip()
        event_date = form_data.get("event_date", "").strip()
        if event_date:
            try:
                from datetime import datetime as _dt

                event_date = _dt.strptime(event_date, "%Y-%m-%d").strftime("%d-%m-%Y")
            except ValueError:
                pass
        label = f"{event_name} {event_date}".strip()
    if not label:
        label = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_session(label, form_data)
    return jsonify({"ok": True})


@app.route("/schedule", methods=["POST"])
def schedule():
    schedules = generate_all(request.form)
    if not schedules:
        return render_template(
            "index.html",
            categories=CATEGORIES,
            category_order=CATEGORY_ORDER,
            total_game_times=TOTAL_GAME_TIMES,
            recommended_match_times=RECOMMENDED_MATCH_TIMES,
            error="Seleziona almeno una categoria.",
        )
    return render_template(
        "schedule.html",
        schedules=schedules,
        categories=CATEGORIES,
        form_data=request.form,
        event_name=request.form.get("event_name", "").strip(),
        event_date=request.form.get("event_date", "").strip(),
    )


@app.route("/download/pdf", methods=["POST"])
def download_pdf():
    schedules = generate_all(request.form)
    event_name = request.form.get("event_name", "").strip()
    event_date = request.form.get("event_date", "").strip()
    include_main = request.form.get("pdf_main", "1") == "1"
    include_field = request.form.get("pdf_field", "1") == "1"
    include_team = request.form.get("pdf_team", "1") == "1"
    pdf_bytes = schedule_to_pdf(
        schedules,
        event_name,
        event_date,
        include_main=include_main,
        include_field=include_field,
        include_team=include_team,
    )
    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="tournament.pdf",
    )


@app.route("/download/excel", methods=["POST"])
def download_excel():
    schedules = generate_all(request.form)
    event_name = request.form.get("event_name", "").strip()
    event_date = request.form.get("event_date", "").strip()
    excel_bytes = schedule_to_excel(schedules, event_name, event_date)
    return send_file(
        BytesIO(excel_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="tournament.xlsx",
    )


if __name__ == "__main__":
    app.run(debug=True, port=5050)
