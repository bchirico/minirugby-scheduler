from io import BytesIO

from fpdf import FPDF
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill

from models import CATEGORIES, Schedule


def schedule_to_pdf(schedules: list[Schedule]) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    for sched in schedules:
        pdf.add_page()
        config = CATEGORIES[sched.category]

        # Title
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 12, f"{sched.category} Schedule", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(
            0, 6,
            f"{len(sched.stats)} teams | {len(sched.matches)} matches | "
            f"{config.match_duration} min + {config.break_duration} min break",
            new_x="LMARGIN", new_y="NEXT",
        )
        pdf.ln(4)

        # Warnings
        for w in sched.warnings:
            pdf.set_font("Helvetica", "I", 9)
            pdf.cell(0, 5, f"Note: {w}", new_x="LMARGIN", new_y="NEXT")
        if sched.warnings:
            pdf.ln(2)

        # Match table
        col_widths = [20, 25, 55, 55, 35]  # #, Time, Field, Match, Referee
        headers = ["#", "Time", "Field", "Match", "Referee"]

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(220, 220, 220)
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 8, h, border=1, fill=True)
        pdf.ln()

        pdf.set_font("Helvetica", "", 9)
        current_slot = -1
        for m in sched.matches:
            if m.time_slot != current_slot:
                current_slot = m.time_slot
                if current_slot > 0:
                    # Light separator between slots
                    pdf.set_fill_color(245, 245, 245)
                    pdf.cell(sum(col_widths), 2, "", border=0, fill=True, new_x="LMARGIN", new_y="NEXT")

            pdf.cell(col_widths[0], 7, str(m.match_number), border=1)
            pdf.cell(col_widths[1], 7, m.start_time, border=1)
            pdf.cell(col_widths[2], 7, f"Field {m.field_number}", border=1)
            pdf.cell(col_widths[3], 7, f"{m.team1} vs {m.team2}", border=1)
            pdf.cell(col_widths[4], 7, m.referee, border=1)
            pdf.ln()

        pdf.ln(6)

        # Stats table
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Fairness Stats", new_x="LMARGIN", new_y="NEXT")

        stat_widths = [60, 40, 40]
        stat_headers = ["Team", "Matches", "Ref Duties"]
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(220, 220, 220)
        for i, h in enumerate(stat_headers):
            pdf.cell(stat_widths[i], 8, h, border=1, fill=True)
        pdf.ln()

        pdf.set_font("Helvetica", "", 9)
        for team, stat in sched.stats.items():
            pdf.cell(stat_widths[0], 7, team, border=1)
            pdf.cell(stat_widths[1], 7, str(stat["played"]), border=1)
            pdf.cell(stat_widths[2], 7, str(stat["refereed"]), border=1)
            pdf.ln()

    return pdf.output()


def schedule_to_excel(schedules: list[Schedule]) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)  # remove default sheet

    header_font = Font(bold=True)
    header_fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")

    for sched in schedules:
        ws = wb.create_sheet(title=sched.category)

        # Schedule table
        headers = ["#", "Time", "Field", "Team 1", "Team 2", "Referee"]
        ws.append(headers)
        for i, cell in enumerate(ws[1], 1):
            cell.font = header_font
            cell.fill = header_fill

        for m in sched.matches:
            ws.append([
                m.match_number,
                m.start_time,
                f"Field {m.field_number}",
                m.team1,
                m.team2,
                m.referee,
            ])

        # Blank row then stats
        ws.append([])
        stats_start = ws.max_row + 1
        ws.append(["Team", "Matches Played", "Referee Duties"])
        for cell in ws[stats_start]:
            if cell.value:
                cell.font = header_font
                cell.fill = header_fill

        for team, stat in sched.stats.items():
            ws.append([team, stat["played"], stat["refereed"]])

        # Auto-width columns
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = max_len + 3

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
