"""Export-Endpoints: PDF, Excel, ICS-Kalender-Feed und Komplett-Backup."""
from __future__ import annotations

import logging
import tempfile
from datetime import UTC, date, datetime
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, Response, StreamingResponse
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.models.database import get_db
from app.models.models import Insurance, Product
from app.scheduler.notification_job import next_recurring_date
from app.services import backup_service

log = logging.getLogger(__name__)
router = APIRouter()

# Zeichen, die Excel als Formel-Beginn interpretiert (Formula Injection)
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _append_text_row(ws, values: list) -> None:
    """Fügt eine Zeile an und erzwingt Text-Zellen für formelartige Strings.

    openpyxl interpretiert Strings mit führendem '=' als Formel — Werte aus
    Nutzereingaben (Name, Vertragsnummer, Notizen) dürfen nie als Formel landen.
    """
    ws.append(values)
    for cell in ws[ws.max_row]:
        if isinstance(cell.value, str) and cell.value.startswith(_FORMULA_PREFIXES):
            cell.data_type = "s"


@router.get("/insurances.xlsx")
def export_insurances_xlsx(db: Session = Depends(get_db)) -> StreamingResponse:
    rows = db.query(Insurance).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "Versicherungen"
    ws.append(
        [
            "Name",
            "Kategorie",
            "Gehört zu",
            "Versicherer",
            "Vertragsnummer",
            "Start",
            "Ende",
            "Prämie EUR",
            "Intervall",
            "Notizen",
        ]
    )
    for r in rows:
        _append_text_row(
            ws,
            [
                r.name,
                r.kategorie.value,
                r.person or "",
                r.versicherer,
                r.vertragsnummer,
                r.start_date.isoformat() if r.start_date else "",
                r.end_date.isoformat() if r.end_date else "",
                r.praemie_eur or 0,
                r.zahlungsintervall.value,
                r.notes or "",
            ],
        )
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="versicherungen.xlsx"'},
    )


@router.get("/insurances.pdf")
def export_insurances_pdf(db: Session = Depends(get_db)) -> StreamingResponse:
    rows = db.query(Insurance).all()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title="Versicherungsübersicht")
    styles = getSampleStyleSheet()
    elements = [Paragraph("Versicherungsübersicht", styles["Title"]), Spacer(1, 12)]

    data = [["Name", "Kategorie", "Versicherer", "Ende", "Prämie €", "Intervall"]]
    for r in rows:
        data.append(
            [
                r.name,
                r.kategorie.value,
                r.versicherer,
                r.end_date.isoformat() if r.end_date else "-",
                f"{r.praemie_eur:.2f}" if r.praemie_eur is not None else "-",
                r.zahlungsintervall.value,
            ]
        )
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1976d2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="versicherungen.pdf"'},
    )


# ---------------------------------------------------------------------------
# Komplett-Backup (ZIP) — Datensicherung per Klick, ohne Konsole
# ---------------------------------------------------------------------------

@router.get("/backup.zip")
def export_backup() -> FileResponse:
    """Komplett-Backup als ZIP: Datenbank, Vektorindex, alle Dokumente und Belege.

    Die Datenbanken werden über die SQLite-Backup-API konsistent kopiert (auch
    bei laufenden Schreibzugriffen). Die ZIP-Datei entsteht in einer Temp-Datei
    und wird nach dem Download automatisch gelöscht.
    """
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        backup_service.write_backup_zip(tmp_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    log.info("Backup-ZIP erstellt (%.1f MB)", tmp_path.stat().st_size / (1024 * 1024))
    return FileResponse(
        tmp_path,
        media_type="application/zip",
        filename=f"versicherung-backup-{date.today().isoformat()}.zip",
        background=BackgroundTask(tmp_path.unlink, missing_ok=True),
    )


@router.get("/backup/status")
def backup_status() -> dict:
    """Stand der automatischen täglichen Backups (letztes Backup, Anzahl, letzter Fehler)."""
    return backup_service.backup_status()


# ---------------------------------------------------------------------------
# ICS-Kalender-Feed (zum Abonnieren in Apple/Google/Thunderbird-Kalendern)
# ---------------------------------------------------------------------------

def _ics_escape(text: str) -> str:
    """Escaped Sonderzeichen gemäß RFC 5545 (Nutzereingaben in SUMMARY etc.)."""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _ics_fold(line: str) -> str:
    """RFC-5545-Zeilenfaltung: lange Zeilen umbrechen, Fortsetzung mit Leerzeichen.

    Konservativ bei 60 Zeichen gefaltet (Grenzwert der Spezifikation sind 75
    Oktette — Umlaute belegen in UTF-8 mehrere Bytes).
    """
    parts: list[str] = []
    while len(line) > 60:
        parts.append(line[:60])
        line = " " + line[60:]
    parts.append(line)
    return "\r\n".join(parts)


def _vevent(uid: str, dtstamp: str, day: date, summary: str, yearly: bool = False) -> list[str]:
    """Ganztägiges VEVENT; yearly=True erzeugt eine jährliche Serie (Kündigungsfristen)."""
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART;VALUE=DATE:{day.strftime('%Y%m%d')}",
        f"SUMMARY:{_ics_escape(summary)}",
    ]
    if yearly:
        lines.append("RRULE:FREQ=YEARLY")
    lines.append("END:VEVENT")
    return lines


@router.get("/calendar.ics")
def export_calendar_ics(db: Session = Depends(get_db)) -> Response:
    """iCalendar-Feed mit allen Fristen — als Abo-URL im Handy-/Familienkalender nutzbar.

    Enthält: Vertragsabläufe, Garantieenden und jährlich wiederkehrende
    Kündigungsfristen ("kündbar bis").
    """
    today = date.today()
    dtstamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Versicherungs-Assistent//DE",
        "CALSCALE:GREGORIAN",
        "X-WR-CALNAME:Versicherungen & Garantien",
    ]

    for r in db.query(Insurance).all():
        if r.end_date:
            lines += _vevent(
                f"insurance-{r.id}-ablauf@versicherungs-assistent",
                dtstamp,
                r.end_date,
                f"Versicherung läuft ab: {r.name} ({r.versicherer})",
            )
        if r.kuendigung_bis_tag and r.kuendigung_bis_monat:
            deadline = next_recurring_date(r.kuendigung_bis_tag, r.kuendigung_bis_monat, today)
            lines += _vevent(
                f"insurance-{r.id}-kuendigung@versicherungs-assistent",
                dtstamp,
                deadline,
                f"Kündigungsfrist: {r.name} ({r.versicherer})",
                yearly=True,
            )

    for p in (
        db.query(Product)
        .filter(Product.warranty_end.isnot(None), Product.archived.is_(False))
        .all()
    ):
        lines += _vevent(
            f"product-{p.id}-garantie@versicherungs-assistent",
            dtstamp,
            p.warranty_end,
            f"Garantie endet: {p.name}",
        )

    lines.append("END:VCALENDAR")
    body = "\r\n".join(_ics_fold(line) for line in lines) + "\r\n"
    return Response(
        content=body,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'inline; filename="versicherungen.ics"'},
    )


@router.get("/products.xlsx")
def export_products_xlsx(db: Session = Depends(get_db)) -> StreamingResponse:
    rows = db.query(Product).all()

    # Build insurance name lookup to avoid raw IDs in the export
    ins_map: dict[int, str] = {
        i.id: f"{i.name} ({i.versicherer})"
        for i in db.query(Insurance).all()
    }

    wb = Workbook()
    ws = wb.active
    ws.title = "Produkte"
    ws.append(["Name", "Kategorie", "Kaufdatum", "Garantieende", "Verknüpfte Versicherung", "Notizen"])
    for r in rows:
        _append_text_row(
            ws,
            [
                r.name,
                r.kategorie,
                r.purchase_date.isoformat() if r.purchase_date else "",
                r.warranty_end.isoformat() if r.warranty_end else "",
                ins_map.get(r.linked_insurance_id, "") if r.linked_insurance_id else "",
                r.notes or "",
            ],
        )
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="produkte.xlsx"'},
    )
