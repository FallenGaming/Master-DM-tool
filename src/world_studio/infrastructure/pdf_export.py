from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

from world_studio.domain.world import World


class PdfExporter:
    def export_world_summary(self, world: World, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        pdf = canvas.Canvas(str(target), pagesize=LETTER)

        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(72, 760, f"World Summary: {world.name}")

        pdf.setFont("Helvetica", 11)
        pdf.drawString(72, 735, f"World Ref: {world.ext_ref}")
        pdf.drawString(72, 720, f"Generated: {datetime.now(UTC).isoformat()}")
        pdf.drawString(72, 705, f"Active RuleSet: {world.active_ruleset_ref or 'none'}")
        pdf.drawString(72, 690, f"Locked: {'yes' if world.is_locked else 'no'}")

        text = pdf.beginText(72, 660)
        text.setFont("Helvetica", 11)
        text.textLine("Description:")
        for line in (world.description or "").splitlines() or ["(no description)"]:
            text.textLine(f"  {line}")
        pdf.drawText(text)

        pdf.showPage()
        pdf.save()
