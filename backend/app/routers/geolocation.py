from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EmailMessage
from app.schemas import RoutingHopOut

router = APIRouter(prefix="/api/geo", tags=["geolocation"])


@router.get("/{email_id}/hops", response_model=list[RoutingHopOut])
def get_hops(email_id: str, db: Session = Depends(get_db)):
    """Return the geolocated routing hop chain for one email, ordered origin -> destination."""
    email_row = db.get(EmailMessage, email_id)
    if not email_row:
        raise HTTPException(status_code=404, detail="Email not found")
    return sorted(email_row.hops, key=lambda h: h.hop_index)
