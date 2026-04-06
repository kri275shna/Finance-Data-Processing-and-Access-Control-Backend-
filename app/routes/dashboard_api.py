from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Request

from app.auth import require_admin_or_analyst

router = APIRouter(prefix="/dashboard", tags=["Dashboard"], dependencies=[Depends(require_admin_or_analyst)])

@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    total_income = 0.0
    total_expense = 0.0
    category_breakdown = {}
    recent_transactions = []

    # Get requests (latest first) to use as transactions based on their payload
    requests = db.query(Request).order_by(Request.created_at.desc()).all()

    for req in requests:
        payload = req.payload
        if not isinstance(payload, dict):
            continue
            
        amount = 0.0
        t_type = "unknown"
        cat = payload.get("category", "uncategorized")
        is_transaction = False

        # Attempt to parse as {"type": "income"/"expense", "amount": ...}
        if "type" in payload and "amount" in payload:
            t_type = str(payload["type"]).lower()
            try:
                amount = float(payload["amount"])
            except ValueError:
                continue
                
            if t_type == "income":
                total_income += amount
                is_transaction = True
            elif t_type == "expense":
                total_expense += amount
                is_transaction = True
                
            if is_transaction:
                category_breakdown[cat] = category_breakdown.get(cat, 0.0) + amount

        # Attempt to parse as {"income": ...} or {"expense": ...}
        else:
            inc = payload.get("income", 0)
            exp = payload.get("expense", 0)
            
            try:
                inc = float(inc)
                exp = float(exp)
            except ValueError:
                inc = 0.0
                exp = 0.0

            if inc > 0:
                total_income += inc
                is_transaction = True
                c = payload.get("category", "income")
                category_breakdown[c] = category_breakdown.get(c, 0.0) + inc
                amount = inc
                t_type = "income"
                cat = c

            if exp > 0:
                total_expense += exp
                is_transaction = True
                c = payload.get("category", "expense")
                category_breakdown[c] = category_breakdown.get(c, 0.0) + exp
                amount = exp
                t_type = "expense"
                cat = c

        if is_transaction and len(recent_transactions) < 5:
            recent_transactions.append({
                "id": req.id,
                "amount": amount,
                "type": t_type,
                "category": cat,
                "date": req.created_at.isoformat()
            })

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "net_balance": total_income - total_expense,
        "category_breakdown": category_breakdown,
        "recent_transactions": recent_transactions
    }
