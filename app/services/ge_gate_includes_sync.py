"""Sync gate includes with phase gate items (derived relation)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.ge import GeGate, GeGateGateItemInclude, GeGateItem


def sync_gate_includes_for_phase(db: Session, phase_id: str) -> None:
    """Replace gate includes with exactly all gate_item ids in this phase."""
    db.flush()
    gate = db.query(GeGate).filter(GeGate.phase_id == phase_id).first()
    if gate is None:
        return
    db.query(GeGateGateItemInclude).filter(GeGateGateItemInclude.gate_id == gate.id).delete()
    gate_items = db.query(GeGateItem).filter(GeGateItem.phase_id == phase_id).all()
    for item in gate_items:
        db.add(GeGateGateItemInclude(gate_id=gate.id, gate_item_id=item.id))
