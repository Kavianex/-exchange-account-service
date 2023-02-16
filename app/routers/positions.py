import uuid
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from orm import database, models
from internal import schemas, middleware, enums


router = APIRouter(
    prefix="/position",
    tags=["position"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{account_id}", response_model=list[schemas.PositionOut])
async def get_all_by_account(account_id: uuid.UUID, db: Session = Depends(database.get_db)):
    return models.Position.get_open_positions(account_id=account_id, db=db)


@router.get("/{account_id}/{symbol}", response_model=list[schemas.PositionOut])
async def get_all_by_account_symbol(account_id: uuid.UUID, symbol: str, db: Session = Depends(database.get_db)):
    return db.query(models.Position).filter(
        models.Position.account_id == account_id,
        models.Position.symbol == symbol,
        models.Position.margin > Decimal('0.0'),
    ).order_by(
        models.Position.margin.desc()
    ).all()
