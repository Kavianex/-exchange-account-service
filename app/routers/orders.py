import uuid
from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from orm import database, models
from internal import schemas, middleware, enums

router = APIRouter(
    prefix="/order",
    tags=["order"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{account_id}", response_model=list[schemas.OrderOut])
async def get_all_by_account(account_id: uuid.UUID, db: Session = Depends(database.get_db)):
    return db.query(models.Order).filter(
        models.Order.account_id == account_id,
    ).all()


@router.get("/{account_id}/{symbol}", response_model=list[schemas.OrderOut])
async def get_all_by_account_symbol(account_id: uuid.UUID, symbol: str, db: Session = Depends(database.get_db)):
    return db.query(models.Order).filter(
        models.Order.account_id == account_id,
        models.Order.symbol == symbol,
    ).all()


@router.get("/byId/{order_id}", response_model=schemas.OrderOut)
async def get_all_by_account_symbol(account_id: uuid.UUID, symbol: str, order_id: uuid.UUID, db: Session = Depends(database.get_db)):
    db_order = db.query(models.Order).filter(
        models.Order.account_id == account_id,
        models.Order.symbol == symbol,
        models.Order.id == order_id
    ).first()
    if not db_order:
        raise HTTPException(404)
    return db_order


@router.post("/", response_model=schemas.OrderOut)
async def create(order_in: schemas.OrderIn, db: Session = Depends(database.get_db)):
    order_in = order_in.dict()
    db_order = models.Order(**order_in)
    db_balance = db_order.lock_balance(db=db)
    if not db_balance:
        raise HTTPException(400, "insufficient account balance")
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    # publish
    return db_order
