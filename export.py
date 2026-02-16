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
            0,
            6,
            f"{len(sched.stats)} teams | {len(sched.matches)} matches | "
            f"{config.match_duration} min + {config.break_duration} min break",
            new_x="LMARGIN",
            new_y="NEXT",
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
                    pdf.cell(
                        sum(col_widths),
                        2,
                        "",
                        border=0,
                        fill=True,
                        new_x="LMARGIN",
                        new_y="NEXT",
                    )

            pdf.cell(col_widths[0], 7, str(m.match_number), border=1)
            pdf.cell(col_widths[1], 7, m.start_time, border=1)
            pdf.cell(col_widths[2], 7, f"Field {m.field_number}", border=1)
            pdf.cell(col_widths[3], 7, f"{m.team1} vs {m.team2}", border=1)
            pdf.cell(col_widths[4], 7, m.referee, border=1)
            pdf.ln()

        pdf.ln(6)

        # --- Stats table (left) + Field diagram (right) side by side ---
        # Layout: stats table takes left ~90mm, field diagram on the right
        stats_table_w = 85  # total width of stats columns
        gap = 10  # gap between table and diagram
        draw_w = 80  # fixed field diagram width in mm
        draw_h = draw_w * config.field_width_max / config.field_length_max
        meta_mm = draw_w * config.meta / config.field_length_max

        # Estimate total height needed for this section
        num_teams = len(sched.stats)
        stats_h = 8 + 8 + num_teams * 7  # title + header + rows
        section_h = max(stats_h, draw_h + 20) + 10
        if pdf.get_y() + section_h > pdf.h - pdf.b_margin:
            pdf.add_page()

        section_top = pdf.get_y()

        # -- Stats table (left column) --
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(stats_table_w, 8, "Fairness Stats", new_x="LMARGIN", new_y="NEXT")

        stat_widths = [40, 22, 23]
        stat_headers = ["Team", "Matches", "Ref"]
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(220, 220, 220)
        for i, h in enumerate(stat_headers):
            pdf.cell(stat_widths[i], 7, h, border=1, fill=True)
        pdf.ln()

        pdf.set_font("Helvetica", "", 8)
        for team, stat in sched.stats.items():
            pdf.cell(stat_widths[0], 6, team, border=1)
            pdf.cell(stat_widths[1], 6, str(stat["played"]), border=1)
            pdf.cell(stat_widths[2], 6, str(stat["refereed"]), border=1)
            pdf.ln()

        stats_bottom = pdf.get_y()

        # -- Field diagram (right column) --
        field_x = pdf.l_margin + stats_table_w + gap
        field_y = section_top  # start at same level as stats title

        # Field title
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_xy(field_x, field_y)
        pdf.cell(draw_w, 8, "Field Dimensions")
        field_y += 8

        # Green fill for the field
        pdf.set_fill_color(144, 190, 109)
        pdf.set_draw_color(50, 100, 50)
        pdf.set_line_width(0.5)
        pdf.rect(field_x, field_y, draw_w, draw_h, style="DF")

        # Meta (in-goal) areas — dashed lines
        pdf.set_draw_color(255, 255, 255)
        pdf.set_line_width(0.3)
        pdf.dashed_line(
            field_x + meta_mm,
            field_y,
            field_x + meta_mm,
            field_y + draw_h,
            dash_length=2,
            space_length=1.5,
        )
        pdf.dashed_line(
            field_x + draw_w - meta_mm,
            field_y,
            field_x + draw_w - meta_mm,
            field_y + draw_h,
            dash_length=2,
            space_length=1.5,
        )

        # Meta labels (white on green)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_xy(field_x + 1, field_y + draw_h / 2 - 2)
        pdf.cell(meta_mm - 2, 4, f"{config.meta}m", align="C")
        pdf.set_xy(field_x + draw_w - meta_mm + 1, field_y + draw_h / 2 - 2)
        pdf.cell(meta_mm - 2, 4, f"{config.meta}m", align="C")

        # Reset colors
        pdf.set_text_color(0, 0, 0)
        pdf.set_draw_color(0, 0, 0)

        # Length label (below field)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_xy(field_x, field_y + draw_h + 1)
        pdf.cell(draw_w, 4, config.field_length, align="C")

        # Width label (right of field)
        pdf.set_xy(field_x + draw_w + 2, field_y + draw_h / 2 - 2)
        pdf.cell(20, 4, config.field_width)

        # Move cursor below whichever column is taller
        pdf.set_y(max(stats_bottom, field_y + draw_h + 8) + 4)

    return pdf.output()


def schedule_to_excel(schedules: list[Schedule]) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)  # remove default sheet

    header_font = Font(bold=True)
    header_fill = PatternFill(
        start_color="DDDDDD", end_color="DDDDDD", fill_type="solid"
    )

    for sched in schedules:
        ws = wb.create_sheet(title=sched.category)

        # Schedule table
        headers = ["#", "Time", "Field", "Team 1", "Team 2", "Referee"]
        ws.append(headers)
        for i, cell in enumerate(ws[1], 1):
            cell.font = header_font
            cell.fill = header_fill

        for m in sched.matches:
            ws.append(
                [
                    m.match_number,
                    m.start_time,
                    f"Field {m.field_number}",
                    m.team1,
                    m.team2,
                    m.referee,
                ]
            )

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
