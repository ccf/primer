import bcrypt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.database import get_db
from primer.common.models import Engineer


def require_admin(x_admin_key: str = Header()) -> str:
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    return x_admin_key


def verify_api_key(api_key: str, db: Session) -> Engineer:
    """Verify an API key against stored hashes. Returns the engineer or raises."""
    engineers = db.query(Engineer).all()
    for eng in engineers:
        if bcrypt.checkpw(api_key.encode(), eng.api_key_hash.encode()):
            return eng
    raise HTTPException(status_code=401, detail="Invalid API key")


def require_engineer(
    x_api_key: str = Header(), db: Session = Depends(get_db)
) -> Engineer:
    return verify_api_key(x_api_key, db)
