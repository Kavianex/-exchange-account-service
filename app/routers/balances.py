from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from orm import database, models
from internal import schemas, middleware, enums
import uuid
from decimal import Decimal
import settings

router = APIRouter(
    prefix="/balance",
    tags=["balance"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{account_id}", response_model=list[schemas.BalanceOut])
async def get_all(account_id: uuid.UUID, db: Session = Depends(database.get_db)):
    return db.query(models.Balance).filter(models.Balance.account_id == account_id).all()


# @router.post("/", response_model=schemas.BalanceOut, dependencies=[Depends(middleware.verify_admin)])
# async def create(balance_in: schemas.BalanceIn, db: Session = Depends(database.get_db)):
#     return models.Balance.update_or_create(balance_in=balance_in, db=db)


# @router.put("/", response_model=schemas.BalanceOut, dependencies=[Depends(middleware.verify_admin_or_service)])
# async def update(balance_in: schemas.BalanceIn, db: Session = Depends(database.get_db)):
#     return models.Balance.update_or_create(balance_in=balance_in, db=db)


@router.put("/setFreeBalance", response_model=schemas.BalanceOut)
async def update(balance: schemas.Balance, db: Session = Depends(database.get_db)):
    if not settings.TESTNET_APPLICATION:
        return HTTPException(403)
    if models.Position.get_open_positions(account_id=balance.account_id, db=db):
        raise HTTPException(status_code=400, detail="You have open positions")
    elif models.Order.filter_open_orders(account_id=balance.account_id, db=db):
        raise HTTPException(status_code=400, detail="You have open orders")
    else:
        pass
    balance_in = schemas.BalanceIn(
        account_id=balance.account_id,
        asset=enums.CollateralAsset.usdt.value,
        free=Decimal("1000000"),
        locked=Decimal("0.0"),
    )
    db_balance = models.Balance.update_or_create(balance_in=balance_in, db=db)
    schemas.BalanceOut.from_orm(db_balance).publish(
        event_type=enums.EventType.balance.value)
    return db_balance
