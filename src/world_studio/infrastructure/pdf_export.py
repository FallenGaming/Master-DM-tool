from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

from world_studio.domain.world import World


class PdfExporter:
    def export_world_summary(
        self,
        world: World,
        target: Path,
        *,
        pack_kind: str = "summary",
        hierarchy_payload: dict[str, list[dict[str, Any]]] | None = None,
        social_payload: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        pdf = canvas.Canvas(str(target), pagesize=LETTER)

        self._draw_cover(
            pdf,
            world=world,
            pack_kind=pack_kind,
            include_page_break=pack_kind in {"dm", "player"},
        )
        if pack_kind in {"dm", "player"}:
            self._draw_counts_page(
                pdf,
                world=world,
                hierarchy_payload=hierarchy_payload or {},
                social_payload=social_payload or {},
                pack_kind=pack_kind,
            )
            self._draw_settlement_page(
                pdf,
                hierarchy_payload=hierarchy_payload or {},
                pack_kind=pack_kind,
            )
            self._draw_social_page(
                pdf,
                social_payload=social_payload or {},
                pack_kind=pack_kind,
            )
        pdf.save()

    def _draw_cover(
        self,
        pdf: canvas.Canvas,
        *,
        world: World,
        pack_kind: str,
        include_page_break: bool,
    ) -> None:
        title = f"World Pack ({pack_kind.title()}): {world.name}"
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(72, 760, title)

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
        if pack_kind == "player":
            text.textLine("")
            text.textLine("Player-safe pack: strategic refs and private notes omitted.")
        elif pack_kind == "dm":
            text.textLine("")
            text.textLine("DM pack: includes detailed metrics and references.")
        pdf.drawText(text)
        if include_page_break:
            pdf.showPage()

    def _draw_counts_page(
        self,
        pdf: canvas.Canvas,
        *,
        world: World,
        hierarchy_payload: dict[str, list[dict[str, Any]]],
        social_payload: dict[str, list[dict[str, Any]]],
        pack_kind: str,
    ) -> None:
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(72, 760, f"{world.name} - Structural Overview")
        pdf.setFont("Helvetica", 11)
        y = 735
        for label, count in (
            ("Continents", len(hierarchy_payload.get("continents", []))),
            ("Empires", len(hierarchy_payload.get("empires", []))),
            ("Kingdoms", len(hierarchy_payload.get("kingdoms", []))),
            ("Regions", len(hierarchy_payload.get("regions", []))),
            ("Settlements", len(hierarchy_payload.get("settlements", []))),
            ("Points of Interest", len(hierarchy_payload.get("points_of_interest", []))),
            ("Routes", len(hierarchy_payload.get("routes", []))),
            ("NPCs", len(social_payload.get("npcs", []))),
            ("Relationships", len(social_payload.get("relationships", []))),
        ):
            pdf.drawString(72, y, f"- {label}: {count}")
            y -= 16
        if pack_kind == "player":
            pdf.drawString(72, y - 10, "Some sensitive metrics are intentionally hidden.")
        pdf.showPage()

    def _draw_settlement_page(
        self,
        pdf: canvas.Canvas,
        *,
        hierarchy_payload: dict[str, list[dict[str, Any]]],
        pack_kind: str,
    ) -> None:
        settlements = sorted(
            hierarchy_payload.get("settlements", []),
            key=lambda item: int(item.get("population", 0)),
            reverse=True,
        )[:24]
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(72, 760, "Settlement Highlights")
        pdf.setFont("Helvetica", 10)
        y = 738
        for settlement in settlements:
            name = str(settlement.get("name", "Unnamed"))
            kind = str(settlement.get("kind", "unknown"))
            population = int(settlement.get("population", 0))
            if pack_kind == "player":
                line = f"- {name} ({kind}) pop. {population}"
            else:
                line = (
                    f"- {name} ({kind}) pop. {population} "
                    f"res={float(settlement.get('resource_index', 0.0)):.2f} "
                    f"safe={float(settlement.get('safety_index', 0.0)):.2f} "
                    f"ref={settlement.get('ext_ref', '')}"
                )
            pdf.drawString(72, y, line[:112])
            y -= 14
            if y < 72:
                pdf.showPage()
                pdf.setFont("Helvetica", 10)
                y = 760
        pdf.showPage()

    def _draw_social_page(
        self,
        pdf: canvas.Canvas,
        *,
        social_payload: dict[str, list[dict[str, Any]]],
        pack_kind: str,
    ) -> None:
        npcs = social_payload.get("npcs", [])[:30]
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(72, 760, "Social Graph Highlights")
        pdf.setFont("Helvetica", 10)
        y = 738
        for npc in npcs:
            display_name = str(npc.get("display_name", "Unknown"))
            occupation_ref = str(npc.get("occupation_ref") or "unassigned")
            if pack_kind == "player":
                line = f"- {display_name} ({occupation_ref})"
            else:
                line = (
                    f"- {display_name} ({occupation_ref}) "
                    f"wealth={float(npc.get('wealth_index', 0.0)):.2f} "
                    f"health={float(npc.get('health_index', 0.0)):.2f} "
                    f"ref={npc.get('ext_ref', '')}"
                )
            pdf.drawString(72, y, line[:112])
            y -= 14
            if y < 72:
                pdf.showPage()
                pdf.setFont("Helvetica", 10)
                y = 760
        pdf.showPage()
