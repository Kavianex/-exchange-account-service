import uuid
from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from orm import database, models
from internal import schemas, middleware, enums
from sqlalchemy.sql import text


router = APIRouter(
    prefix="/trade",
    tags=["trade"],
    responses={404: {"description": "Not found"}},
)


@router.get("/byId/{trade_id}", response_model=schemas.SubTradeOut)
async def get_by_id(trade_id: uuid.UUID, db: Session = Depends(database.get_db)):
    query = f"""
        select 
        subtrades.id, commission, commission_asset, subtrades.side, is_maker,
        trades.insert_time,
        case
            when is_maker then trades.maker_order_id
        else
            trades.taker_order_id
        end as order_id,
        orders.account_id,
        orders.symbol,
        trades.price,
        trades.quantity,
        trades.quote_quantity
        from subtrades
        left join trades 
        on trade_id = trades.id
        left JOIN orders
        on 
        case
            when is_maker then trades.maker_order_id = orders.id
        else
            trades.taker_order_id = orders.id
        end
        where subtrades.id = :trade_id;
    """
    db_query = db.execute(text(query), {'trade_id': str(trade_id)})
    db_sub_trade = db_query.first()
    if not db_sub_trade:
        raise HTTPException(404)
    return db_sub_trade


@router.get("/byOrder/{order_id}", response_model=list[schemas.SubTradeOut])
async def get_all_by_order(order_id: uuid.UUID, db: Session = Depends(database.get_db)):
    query = f"""
        select 
        subtrades.id, commission, commission_asset, subtrades.side, is_maker,
        trades.insert_time,
        case
            when is_maker then trades.maker_order_id
        else
            trades.taker_order_id
        end as order_id,
        orders.account_id,
        orders.symbol,
        trades.price,
        trades.quantity,
        trades.quote_quantity
        from subtrades
        left join trades 
        on trade_id = trades.id
        left JOIN orders
        on 
        case
            when is_maker then trades.maker_order_id = orders.id
        else
            trades.taker_order_id = orders.id
        end
        where orders.id = :order_id;
    """
    return db.execute(text(query), {'order_id': str(order_id)}).all()


@router.get("/{account_id}", response_model=list[schemas.SubTradeOut])
async def get_all_by_account(account_id: uuid.UUID, db: Session = Depends(database.get_db)):
    query = f"""
        select 
        subtrades.id, commission, commission_asset, subtrades.side, is_maker,
        trades.insert_time,
        case
            when is_maker then trades.maker_order_id
        else
            trades.taker_order_id
        end as order_id,
        orders.account_id,
        orders.symbol,
        trades.price,
        trades.quantity,
        trades.quote_quantity
        from subtrades
        left join trades 
        on trade_id = trades.id
        left JOIN orders
        on 
        case
            when is_maker then trades.maker_order_id = orders.id
        else
            trades.taker_order_id = orders.id
        end
        where orders.account_id = :account_id;
    """
    return db.execute(text(query), {'account_id': str(account_id)}).all()


@router.get("/{account_id}/{symbol}", response_model=list[schemas.SubTradeOut])
async def get_all_by_account_symbol(account_id: uuid.UUID, symbol: str, db: Session = Depends(database.get_db)):
    query = f"""
        select 
        subtrades.id, commission, commission_asset, subtrades.side, is_maker,
        trades.insert_time,
        case
            when is_maker then trades.maker_order_id
        else
            trades.taker_order_id
        end as order_id,
        orders.account_id,
        orders.symbol,
        trades.price,
        trades.quantity,
        trades.quote_quantity
        from subtrades
        left join trades 
        on trade_id = trades.id
        left JOIN orders
        on 
        case
            when is_maker then trades.maker_order_id = orders.id
        else
            trades.taker_order_id = orders.id
        end
        where orders.account_id = :account_id and orders.symbol = :symbol;
    """
    return db.execute(text(query), {'account_id': str(account_id), 'symbol': symbol}).all()
