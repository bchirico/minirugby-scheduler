from datetime import datetime
from io import BytesIO

from fpdf import FPDF
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from models import CATEGORIES, U6_FIELD_FORMATS, Schedule


def _format_date(date_str: str) -> str:
    """Convert YYYY-MM-DD to DD/MM/YYYY, return as-is if not parseable."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return date_str


def schedule_to_pdf(schedules: list[Schedule], event_name: str = "", event_date: str = "") -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    if event_name or event_date:
        pdf.add_page()
        if event_name:
            pdf.set_font("Helvetica", "B", 22)
            pdf.cell(0, 14, event_name, new_x="LMARGIN", new_y="NEXT", align="C")
        if event_date:
            pdf.set_font("Helvetica", "", 13)
            pdf.cell(0, 8, _format_date(event_date), new_x="LMARGIN", new_y="NEXT", align="C")

    for sched in schedules:
        pdf.add_page()
        config = CATEGORIES[sched.category]

        # Title
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 12, f"Calendario {sched.category}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(
            0,
            6,
            f"{len(sched.stats)} squadre | {len(sched.matches)} partite | "
            f"{sched.match_duration} min + {sched.break_duration} min pausa",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.ln(4)

        # Warnings
        for w in sched.warnings:
            pdf.set_font("Helvetica", "I", 9)
            pdf.cell(0, 5, f"Nota: {w}", new_x="LMARGIN", new_y="NEXT")
        if sched.warnings:
            pdf.ln(2)

        # Match table — Arbitro column omitted when no_referee
        if sched.no_referee:
            col_widths = [20, 25, 65, 80]  # #, Time, Field, Match
            headers = ["#", "Orario", "Campo", "Partita"]
        else:
            col_widths = [20, 25, 55, 55, 35]  # #, Time, Field, Match, Referee
            headers = ["#", "Orario", "Campo", "Partita", "Arbitro"]

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(220, 220, 220)
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 8, h, border=1, fill=True)
        pdf.ln()

        resting_per_slot = sched.resting_per_slot
        current_slot = -1
        for m in sched.matches:
            if m.time_slot != current_slot:
                if current_slot >= 0:
                    # Riposa row for the slot that just ended
                    resting = resting_per_slot.get(current_slot, [])
                    if resting:
                        pdf.set_font("Helvetica", "I", 8)
                        pdf.set_fill_color(248, 248, 248)
                        pdf.cell(
                            sum(col_widths),
                            6,
                            f"Riposa: {', '.join(resting)}",
                            border=1,
                            fill=True,
                            new_x="LMARGIN",
                            new_y="NEXT",
                        )
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
                current_slot = m.time_slot

            pdf.set_font("Helvetica", "", 9)
            pdf.cell(col_widths[0], 7, str(m.match_number), border=1)
            pdf.cell(col_widths[1], 7, m.start_time, border=1)
            pdf.cell(col_widths[2], 7, f"Campo {m.field_number}", border=1)
            pdf.cell(col_widths[3], 7, f"{m.team1} vs {m.team2}", border=1)
            if not sched.no_referee:
                pdf.cell(col_widths[4], 7, m.referee, border=1)
            pdf.ln()

        # Riposa row for the last slot
        if current_slot >= 0:
            resting = resting_per_slot.get(current_slot, [])
            if resting:
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_fill_color(248, 248, 248)
                pdf.cell(
                    sum(col_widths),
                    6,
                    f"Riposa: {', '.join(resting)}",
                    border=1,
                    fill=True,
                    new_x="LMARGIN",
                    new_y="NEXT",
                )

        pdf.ln(6)

        # --- Stats table (left) + Field diagram (right) side by side ---
        stats_table_w = 95
        gap = 10
        draw_w = 80
        draw_h = draw_w * config.field_width_max / config.field_length_max
        meta_mm = draw_w * config.meta / config.field_length_max

        num_teams = len(sched.stats)
        stats_h = 8 + 8 + num_teams * 7
        section_h = max(stats_h, draw_h + 20) + 10
        if pdf.get_y() + section_h > pdf.h - pdf.b_margin:
            pdf.add_page()

        section_top = pdf.get_y()

        # -- Stats table (left column) --
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(stats_table_w, 8, "Statistiche", new_x="LMARGIN", new_y="NEXT")

        if sched.no_referee:
            stat_widths = [55, 18, 22]
            stat_headers = ["Squadra", "Partite", "Max Attesa"]
        else:
            stat_widths = [35, 18, 20, 22]
            stat_headers = ["Squadra", "Partite", "Arbitraggi", "Max Attesa"]

        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(220, 220, 220)
        for i, h in enumerate(stat_headers):
            pdf.cell(stat_widths[i], 7, h, border=1, fill=True)
        pdf.ln()

        pdf.set_font("Helvetica", "", 8)
        for team, stat in sched.stats.items():
            pdf.cell(stat_widths[0], 6, team, border=1)
            pdf.cell(stat_widths[1], 6, str(stat["played"]), border=1)
            if not sched.no_referee:
                pdf.cell(stat_widths[2], 6, str(stat["refereed"]), border=1)
                pdf.cell(stat_widths[3], 6, f"{stat['max_wait']} min", border=1)
            else:
                pdf.cell(stat_widths[2], 6, f"{stat['max_wait']} min", border=1)
            pdf.ln()

        stats_bottom = pdf.get_y()

        # -- Field diagram (right column) --
        field_x = pdf.l_margin + stats_table_w + gap
        field_y = section_top

        pdf.set_font("Helvetica", "B", 11)
        pdf.set_xy(field_x, field_y)
        pdf.cell(draw_w, 8, "Dimensioni Campo")
        field_y += 8

        pdf.set_fill_color(144, 190, 109)
        pdf.set_draw_color(50, 100, 50)
        pdf.set_line_width(0.5)
        pdf.rect(field_x, field_y, draw_w, draw_h, style="DF")

        pdf.set_draw_color(255, 255, 255)
        pdf.set_line_width(0.3)
        pdf.dashed_line(
            field_x + meta_mm, field_y,
            field_x + meta_mm, field_y + draw_h,
            dash_length=2, space_length=1.5,
        )
        pdf.dashed_line(
            field_x + draw_w - meta_mm, field_y,
            field_x + draw_w - meta_mm, field_y + draw_h,
            dash_length=2, space_length=1.5,
        )

        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_xy(field_x + 1, field_y + draw_h / 2 - 2)
        pdf.cell(meta_mm - 2, 4, f"{config.meta}m", align="C")
        pdf.set_xy(field_x + draw_w - meta_mm + 1, field_y + draw_h / 2 - 2)
        pdf.cell(meta_mm - 2, 4, f"{config.meta}m", align="C")

        pdf.set_text_color(0, 0, 0)
        pdf.set_draw_color(0, 0, 0)

        pdf.set_font("Helvetica", "", 8)
        pdf.set_xy(field_x, field_y + draw_h + 1)
        pdf.cell(draw_w, 4, config.field_length, align="C")
        pdf.set_xy(field_x + draw_w + 2, field_y + draw_h / 2 - 2)
        pdf.cell(20, 4, config.field_width)

        # For U6, list all 3 field formats below the diagram
        if sched.category == "U6":
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_xy(field_x, field_y + draw_h + 6)
            pdf.cell(draw_w, 5, "Dimensioni variabili in base al numero di giocatori:", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 8)
            for players, fmt in U6_FIELD_FORMATS.items():
                pdf.set_x(field_x)
                pdf.cell(
                    draw_w, 4,
                    f"{players} vs {players}:  {fmt['field_width']} \u00d7 {fmt['field_length']}",
                    new_x="LMARGIN", new_y="NEXT",
                )

        pdf.set_y(max(stats_bottom, field_y + draw_h + 8) + 4)

    return pdf.output()


def schedule_to_excel(schedules: list[Schedule], event_name: str = "", event_date: str = "") -> bytes:
    wb = Workbook()
    wb.remove(wb.active)

    header_font = Font(bold=True)
    header_fill = PatternFill(
        start_color="DDDDDD", end_color="DDDDDD", fill_type="solid"
    )

    for sched in schedules:
        ws = wb.create_sheet(title=sched.category)

        # Event header
        if event_name or event_date:
            header_parts = [p for p in [event_name, _format_date(event_date) if event_date else ""] if p]
            ws.append([" — ".join(header_parts)])
            ws.cell(ws.max_row, 1).font = Font(bold=True, size=13)
            ws.append([])

        # Schedule table
        if sched.no_referee:
            headers = ["#", "Orario", "Campo", "Squadra 1", "Squadra 2"]
        else:
            headers = ["#", "Orario", "Campo", "Squadra 1", "Squadra 2", "Arbitro"]
        ws.append(headers)
        for cell in ws[ws.max_row]:
            cell.font = header_font
            cell.fill = header_fill

        resting_per_slot_xl = sched.resting_per_slot
        current_slot_xl = -1
        num_cols = len(headers)
        for m in sched.matches:
            if m.time_slot != current_slot_xl:
                if current_slot_xl >= 0:
                    resting = resting_per_slot_xl.get(current_slot_xl, [])
                    if resting:
                        row = [f"Riposa: {', '.join(resting)}"] + [""] * (num_cols - 1)
                        ws.append(row)
                        ws.cell(ws.max_row, 1).font = Font(italic=True, color="888888")
                current_slot_xl = m.time_slot
            row = [m.match_number, m.start_time, f"Campo {m.field_number}", m.team1, m.team2]
            if not sched.no_referee:
                row.append(m.referee)
            ws.append(row)

        # Riposa for the last slot
        if current_slot_xl >= 0:
            resting = resting_per_slot_xl.get(current_slot_xl, [])
            if resting:
                row = [f"Riposa: {', '.join(resting)}"] + [""] * (num_cols - 1)
                ws.append(row)
                ws.cell(ws.max_row, 1).font = Font(italic=True, color="888888")

        # Blank row then stats
        ws.append([])
        stats_start = ws.max_row + 1
        if sched.no_referee:
            ws.append(["Squadra", "Partite Giocate", "Max Attesa (min)"])
        else:
            ws.append(["Squadra", "Partite Giocate", "Arbitraggi", "Max Attesa (min)"])
        for cell in ws[stats_start]:
            if cell.value:
                cell.font = header_font
                cell.fill = header_fill

        for team, stat in sched.stats.items():
            if sched.no_referee:
                ws.append([team, stat["played"], stat["max_wait"]])
            else:
                ws.append([team, stat["played"], stat["refereed"], stat["max_wait"]])

        # Auto-width columns
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = max_len + 3

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
