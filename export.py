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


def _render_match_table(pdf, matches, sched, col_widths, headers, *, show_resting=True):
    """Render the match table (header + rows + riposa + lunch break)."""
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(220, 220, 220)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, fill=True)
    pdf.ln()

    resting_per_slot = sched.resting_per_slot
    current_slot = -1
    for m in matches:
        if m.time_slot != current_slot:
            if show_resting and current_slot >= 0:
                resting = resting_per_slot.get(current_slot, [])
                if resting:
                    pdf.set_font("Helvetica", "I", 8)
                    pdf.set_fill_color(248, 248, 248)
                    pdf.cell(
                        sum(col_widths),
                        5,
                        f"Riposa: {', '.join(resting)}",
                        border=1,
                        fill=True,
                        new_x="LMARGIN",
                        new_y="NEXT",
                    )
            if sched.morning_slots > 0 and m.time_slot == sched.morning_slots:
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_fill_color(74, 108, 247)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(
                    sum(col_widths),
                    8,
                    f"PAUSA  {sched.lunch_break} min",
                    border=0,
                    fill=True,
                    align="C",
                    new_x="LMARGIN",
                    new_y="NEXT",
                )
                pdf.set_text_color(0, 0, 0)
            current_slot = m.time_slot

        pdf.set_font("Helvetica", "", 9)
        pdf.cell(col_widths[0], 8, str(m.match_number), border=1)
        pdf.cell(col_widths[1], 8, m.start_time, border=1)
        pdf.cell(col_widths[2], 8, f"Campo {m.field_number}", border=1)
        pdf.cell(col_widths[3], 8, f"{m.team1} vs {m.team2}", border=1)
        if not sched.no_referee:
            pdf.cell(col_widths[4], 8, m.referee, border=1)
        pdf.cell(col_widths[-1], 8, "", border=1)
        pdf.ln()

    # Riposa row for the last slot
    if show_resting and current_slot >= 0:
        resting = resting_per_slot.get(current_slot, [])
        if resting:
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_fill_color(248, 248, 248)
            pdf.cell(
                sum(col_widths),
                5,
                f"Riposa: {', '.join(resting)}",
                border=1,
                fill=True,
                new_x="LMARGIN",
                new_y="NEXT",
            )


def _render_field_match_table(pdf, matches, sched):
    """Render per-field table with two rows per match (one per team) + Risultato/Punti."""
    if sched.no_referee:
        col_widths = [30, 80, 40, 40]
        headers = ["Orario", "Squadra", "Risultato", "Punti"]
    else:
        col_widths = [25, 35, 60, 35, 35]
        headers = ["Orario", "Arbitro", "Squadra", "Risultato", "Punti"]
    row_h = 8
    thick = 0.4
    thin = 0.15

    pdf.set_line_width(thick)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(220, 220, 220)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], row_h, h, border=1, fill=True, align="C")
    pdf.ln()

    current_slot = -1
    for m in matches:
        if m.time_slot != current_slot:
            if sched.morning_slots > 0 and m.time_slot == sched.morning_slots:
                pdf.set_line_width(thick)
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_fill_color(74, 108, 247)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(
                    sum(col_widths),
                    row_h,
                    f"PAUSA  {sched.lunch_break} min",
                    border=0,
                    fill=True,
                    align="C",
                    new_x="LMARGIN",
                    new_y="NEXT",
                )
                pdf.set_text_color(0, 0, 0)
            current_slot = m.time_slot

        y_start = pdf.get_y()
        pdf.set_font("Helvetica", "", 9)

        # Spanning cells: Orario (and Arbitro if present)
        pdf.set_line_width(thick)
        pdf.cell(col_widths[0], row_h * 2, m.start_time, border=1, align="C")
        if not sched.no_referee:
            pdf.cell(col_widths[1], row_h * 2, m.referee, border=1, align="C")
        x_team = pdf.get_x()

        # Team 1 row — thick on top/left/right, no bottom
        pdf.cell(col_widths[-3], row_h, m.team1, border="LTR")
        pdf.cell(col_widths[-2], row_h, "", border="LTR")
        pdf.cell(col_widths[-1], row_h, "", border="LTR")

        # Thin horizontal separator between the two team rows
        pdf.set_line_width(thin)
        x_end = x_team + sum(col_widths[-3:])
        pdf.line(x_team, y_start + row_h, x_end, y_start + row_h)

        # Team 2 row — thick on bottom/left/right, no top
        pdf.set_xy(x_team, y_start + row_h)
        pdf.set_line_width(thick)
        pdf.cell(col_widths[-3], row_h, m.team2, border="LBR")
        pdf.cell(col_widths[-2], row_h, "", border="LBR")
        pdf.cell(col_widths[-1], row_h, "", border="LBR")

        pdf.set_xy(pdf.l_margin, y_start + row_h * 2)

    pdf.set_line_width(0.2)  # reset default


def _render_team_page(pdf, team_name, sched, event_name, event_date):
    """Render a per-team page showing their chronological activity."""
    pdf.add_page()

    # Event header
    if event_name or event_date:
        parts = [p for p in [event_name, _format_date(event_date) if event_date else ""] if p]
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 5, " - ".join(parts), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, f"{sched.category} - {team_name}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Table
    col_widths = [30, 25, 30, 105]
    headers = ["Orario", "Campo", "Attivita", "Dettagli"]

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(220, 220, 220)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, fill=True, align="C")
    pdf.ln()

    slots = sorted({m.time_slot for m in sched.matches})
    resting_per_slot = sched.resting_per_slot

    for slot in slots:
        # Lunch break
        if sched.morning_slots > 0 and slot == sched.morning_slots:
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_fill_color(74, 108, 247)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(
                sum(col_widths),
                8,
                f"PAUSA  {sched.lunch_break} min",
                border=0,
                fill=True,
                align="C",
                new_x="LMARGIN",
                new_y="NEXT",
            )
            pdf.set_text_color(0, 0, 0)

        slot_matches = [m for m in sched.matches if m.time_slot == slot]
        start_time = slot_matches[0].start_time

        activity = ""
        campo = ""
        details = ""

        for m in slot_matches:
            if team_name in (m.team1, m.team2):
                activity = "Gioca"
                campo = str(m.field_number)
                opponent = m.team2 if team_name == m.team1 else m.team1
                details = f"vs {opponent}"
                break
            if not sched.no_referee and m.referee == team_name:
                activity = "Arbitra"
                campo = str(m.field_number)
                details = f"{m.team1} vs {m.team2}"
                break

        if not activity and team_name in resting_per_slot.get(slot, []):
            activity = "Riposa"

        if not activity:
            continue

        pdf.set_font("Helvetica", "", 9)
        pdf.cell(col_widths[0], 8, start_time, border=1, align="C")
        pdf.cell(col_widths[1], 8, campo, border=1, align="C")
        pdf.cell(col_widths[2], 8, activity, border=1, align="C")
        pdf.cell(col_widths[3], 8, details, border=1)
        pdf.ln()


def schedule_to_pdf(schedules: list[Schedule], event_name: str = "", event_date: str = "") -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    for sched in schedules:
        pdf.add_page()
        config = CATEGORIES[sched.category]

        # Event header (small, top of each category page)
        if event_name or event_date:
            parts = [p for p in [event_name, _format_date(event_date) if event_date else ""] if p]
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 5, " - ".join(parts), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

        # Title
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 12, f"Calendario {sched.category}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        if sched.half_time_interval > 0:
            half = sched.match_duration // 2
            match_desc = (
                f"{half} min + {half} min ({sched.half_time_interval} min intervallo)"
            )
        else:
            match_desc = f"{sched.match_duration} min"
        pdf.cell(
            0,
            6,
            f"{len(sched.stats)} squadre | {len(sched.matches)} partite | "
            f"{match_desc} + {sched.break_duration} min pausa",
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
            col_widths = [15, 25, 55, 65, 30]  # #, Time, Field, Match, Result
            headers = ["#", "Orario", "Campo", "Partita", "Risultato"]
        else:
            col_widths = [15, 25, 45, 50, 25, 30]  # #, Time, Field, Match, Referee, Result
            headers = ["#", "Orario", "Campo", "Partita", "Arbitro", "Risultato"]

        _render_match_table(pdf, sched.matches, sched, col_widths, headers)

        pdf.ln(3)

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

        # --- Per-field pages ---
        field_numbers = sorted({m.field_number for m in sched.matches})
        for fn in field_numbers:
            pdf.add_page()

            # Event header
            if event_name or event_date:
                parts = [p for p in [event_name, _format_date(event_date) if event_date else ""] if p]
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 5, " - ".join(parts), new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(0, 0, 0)
                pdf.ln(2)

            # Title
            pdf.set_font("Helvetica", "B", 18)
            pdf.cell(0, 12, f"{sched.category} - Campo {fn}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)

            field_matches = [m for m in sched.matches if m.field_number == fn]
            _render_field_match_table(pdf, field_matches, sched)

        # --- Per-team pages ---
        for team_name in sched.stats:
            _render_team_page(pdf, team_name, sched, event_name, event_date)

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
            ws.append([" - ".join(header_parts)])
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
        lunch_fill = PatternFill(start_color="4A6CF7", end_color="4A6CF7", fill_type="solid")
        for m in sched.matches:
            if m.time_slot != current_slot_xl:
                if current_slot_xl >= 0:
                    resting = resting_per_slot_xl.get(current_slot_xl, [])
                    if resting:
                        row = [f"Riposa: {', '.join(resting)}"] + [""] * (num_cols - 1)
                        ws.append(row)
                        ws.cell(ws.max_row, 1).font = Font(italic=True, color="888888")
                # Lunch break row
                if sched.morning_slots > 0 and m.time_slot == sched.morning_slots:
                    row = [f"PAUSA  {sched.lunch_break} min"] + [""] * (num_cols - 1)
                    ws.append(row)
                    for cell in ws[ws.max_row]:
                        cell.font = Font(bold=True, color="FFFFFF")
                        cell.fill = lunch_fill
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
