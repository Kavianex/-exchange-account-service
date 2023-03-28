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


@router.get("/byId/{order_id}", response_model=schemas.OrderOut)
async def get_all_by_account_symbol(order_id: uuid.UUID, db: Session = Depends(database.get_db)):
    db_order = db.query(models.Order).filter(
        models.Order.id == order_id
    ).first()
    if not db_order:
        raise HTTPException(404)
    return db_order


@router.get("/open/{account_id}", response_model=list[schemas.OrderOut])
async def get_all_by_account(account_id: uuid.UUID, db: Session = Depends(database.get_db)):
    return db.query(models.Order).filter(
        models.Order.account_id == account_id,
        models.Order.status.in_(enums.OrderStatus.open_orders.value),
    ).order_by(
        models.Order.insert_time.desc()
    ).all()


@router.get("/open/{account_id}/{symbol}", response_model=list[schemas.OrderOut])
async def get_all_by_account_symbol(account_id: uuid.UUID, symbol: str, db: Session = Depends(database.get_db)):
    return db.query(models.Order).filter(
        models.Order.account_id == account_id,
        models.Order.status.in_(enums.OrderStatus.open_orders.value),
        models.Order.symbol == symbol,
    ).order_by(
        models.Order.insert_time.desc()
    ).all()


@router.get("/book/{symbol}", response_model=list[schemas.OrderBookOut])
async def get_symbol_order_book(symbol: str, db: Session = Depends(database.get_db)):
    return models.Order.get_order_book(db=db, symbol=symbol)


@router.get("/{account_id}", response_model=list[schemas.OrderOut])
async def get_all_by_account(account_id: uuid.UUID, db: Session = Depends(database.get_db)):
    return db.query(models.Order).filter(
        models.Order.account_id == account_id,
    ).order_by(
        models.Order.insert_time.desc()
    ).all()


@router.get("/{account_id}/{symbol}", response_model=list[schemas.OrderOut])
async def get_all_by_account_symbol(account_id: uuid.UUID, symbol: str, db: Session = Depends(database.get_db)):
    return db.query(models.Order).filter(
        models.Order.account_id == account_id,
        models.Order.symbol == symbol,
    ).order_by(
        models.Order.insert_time.desc()
    ).all()


@router.post("/", response_model=schemas.OrderOut)
async def create(order_in: schemas.OrderIn, account_id:  str = Header(), db: Session = Depends(database.get_db)):
    order_in = order_in.dict()
    order_in['account_id'] = account_id
    account = db.query(models.Account).filter(
        models.Account.id == account_id).one()
    order_in['leverage'] = account.leverage
    db_order = models.Order(**order_in)
    locked_balance = db_order.lock_balance(db=db)
    if not locked_balance:
        raise HTTPException(400, "insufficient balance")
    db.add(db_order)
    db.commit()
    db.close()
    schemas.BalanceOut.from_orm(locked_balance).publish(
        event_type=enums.EventType.balance.value
    )
    order_out = schemas.OrderOut.from_orm(db_order)
    order_out.publish(event_type=enums.EventType.send_order.value)
    return order_out


@router.delete("/byId/{order_id}", response_model=schemas.OrderCancel)
async def get_all_by_account_symbol(order_id: uuid.UUID, db: Session = Depends(database.get_db)):
    db_order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.status.in_(enums.OrderStatus.open_orders.value),
    ).first()
    if not db_order:
        raise HTTPException(404)
    order = schemas.OrderCancel.from_orm(db_order)
    order.cancel_order()
    return order


@router.delete("/{account_id}", response_model=list[schemas.OrderCancel])
async def get_all_by_account(account_id: uuid.UUID, db: Session = Depends(database.get_db)):
    open_orders = models.Order.filter_open_orders(db=db, account_id=account_id)
    return schemas.OrderCancel.cancel_orders(open_orders)


@router.delete("/{account_id}/{symbol}", response_model=list[schemas.OrderCancel])
async def get_all_by_account_symbol(account_id: uuid.UUID, symbol: str, db: Session = Depends(database.get_db)):
    open_orders = models.Order.filter_open_orders(
        db=db,
        account_id=account_id,
        symbol=symbol
    )
    return schemas.OrderCancel.cancel_orders(open_orders)
