"""Connected backend services behind the bounded action set A_routine.

These are deliberately simple stand-ins (they write ActionRecord rows and return a
reference). Swap the bodies for calls to your identity, billing, and CRM systems.
"""
import secrets

from sqlalchemy.orm import Session

from .models import ActionRecord

ROUTINE_ACTIONS = ("password_reset", "refund_initiation", "account_update")


def execute(db: Session, ticket_id: int, action: str, params: dict) -> dict:
    if action not in ROUTINE_ACTIONS:  # defence in depth: never run anything outside A_routine
        return {"executed": False, "reason": "action is outside the routine set"}

    if action == "password_reset":
        result = {"executed": True, "detail": "Password reset email queued for the address on file",
                  "reference": f"PWR-{secrets.token_hex(3).upper()}"}
    elif action == "refund_initiation":
        order = params.get("order_id")
        if not order:
            return {"executed": False, "reason": "order number missing"}
        result = {"executed": True, "detail": f"Refund review opened for order {order}",
                  "reference": f"RFD-{secrets.token_hex(3).upper()}"}
    else:  # account_update
        result = {"executed": True, "detail": "Verification link sent to confirm the profile change",
                  "reference": f"ACC-{secrets.token_hex(3).upper()}"}

    db.add(ActionRecord(ticket_id=ticket_id, type=action, params=params, result=result))
    db.commit()
    return result
