from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User

def get_current_user(x_user_id: str = Header(..., alias="X-User-Id"), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == x_user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Admin role required")
    return user

def require_admin_or_analyst(user: User = Depends(get_current_user)):
    if user.role not in ["admin", "analyst"]:
        raise HTTPException(status_code=403, detail="Forbidden: Admin or Analyst role required")
    return user

def require_any_role(user: User = Depends(get_current_user)):
    if user.role not in ["admin", "analyst", "viewer"]:
        raise HTTPException(status_code=403, detail="Forbidden: Valid role required")
    return user
