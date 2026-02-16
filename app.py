from io import BytesIO

from flask import Flask, render_template, request, send_file

from models import CATEGORIES, ScheduleRequest, Schedule
from scheduler import generate_schedule
from export import schedule_to_pdf, schedule_to_excel

app = Flask(__name__)

CATEGORY_ORDER = ["U8", "U10", "U12"]


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

        team_names = []
        for i in range(1, num_teams + 1):
            name = form.get(f"{cat}_team_{i}", "").strip()
            if name:
                team_names.append(name)

        requests.append(
            ScheduleRequest(
                category=cat,
                num_teams=num_teams,
                num_fields=num_fields,
                start_time=start_time,
                team_names=team_names if len(team_names) == num_teams else [],
            )
        )
    return requests


def generate_all(form) -> list[Schedule]:
    reqs = parse_form(form)
    return [generate_schedule(req) for req in reqs]


@app.route("/")
def index():
    return render_template(
        "index.html", categories=CATEGORIES, category_order=CATEGORY_ORDER
    )


@app.route("/schedule", methods=["POST"])
def schedule():
    schedules = generate_all(request.form)
    if not schedules:
        return render_template(
            "index.html",
            categories=CATEGORIES,
            category_order=CATEGORY_ORDER,
            error="Please enable at least one category.",
        )
    return render_template(
        "schedule.html",
        schedules=schedules,
        categories=CATEGORIES,
        form_data=request.form,
    )


@app.route("/download/pdf", methods=["POST"])
def download_pdf():
    schedules = generate_all(request.form)
    pdf_bytes = schedule_to_pdf(schedules)
    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="tournament.pdf",
    )


@app.route("/download/excel", methods=["POST"])
def download_excel():
    schedules = generate_all(request.form)
    excel_bytes = schedule_to_excel(schedules)
    return send_file(
        BytesIO(excel_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="tournament.xlsx",
    )


if __name__ == "__main__":
    app.run(debug=True, port=5050)
