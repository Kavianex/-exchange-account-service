from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from orm import database, models
from internal import schemas, middleware
import uuid


router = APIRouter(
    prefix="/balance",
    tags=["balance"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{account_id}", response_model=list[schemas.BalanceOut])
async def get_all(account_id: uuid.UUID, db: Session = Depends(database.get_db)):
    return db.query(models.Balance).filter(models.Balance.account_id == account_id).all()


@router.post("/", response_model=schemas.BalanceOut, dependencies=[Depends(middleware.verify_admin)])
async def create(balance_in: schemas.BalanceIn, db: Session = Depends(database.get_db)):
    return models.Balance.update_or_create(balance_in=balance_in, db=db)


@router.put("/", response_model=schemas.BalanceOut, dependencies=[Depends(middleware.verify_admin_or_service)])
async def update(balance_in: schemas.BalanceIn, db: Session = Depends(database.get_db)):
    return models.Balance.update_or_create(balance_in=balance_in, db=db)
