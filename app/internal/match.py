from decimal import Decimal
from sqlalchemy.orm import Session
from orm import database, models
from internal import enums, schemas
import json


def receive_order(event):
    # event = order_event['event']
    query = [models.Order.id == event['id']]
    if event.get('status') == enums.OrderStatus.queued.value:
        event_type = enums.EventType.send_order.value
    else:
        event_type = enums.EventType.cancel_order.value
    db = database.SessionLocal()
    try:
        order = db.query(models.Order).filter(*query).with_for_update().one()
    except Exception as e:
        db.close()
        return False
    order_matched = False
    records = {
        "orders": [],
        "trades": [],
        "sub_trades": [],
        "balances": {'makers': [], 'taker': []},
        "positions": [],
    }
    if event_type == enums.EventType.cancel_order.value:
        new_events = cancel_order(db=db, order=order, records=records)
    else:
        new_events = match_order(
            db=db,
            order=order,
            records=records
        )
        if order.status in enums.OrderStatus.matched_orders.value:
            order_matched = True
        else:
            db.rollback()
            new_events = cancel_order(db=db, order=order, records=records)
    if order_matched:
        db.commit()
    new_events['orders'].append(order)
    new_events['order_book_updates'] = get_order_book_updates(
        db=db,
        sub_trades=new_events['sub_trades'],
        new_order=order,
    )
    publish_new_events(new_events, symbol=order.symbol)
    db.close()


def get_order_book_updates(db: Session, sub_trades: list[models.SubTrade], new_order: models.Order) -> list:
    makers_price_list, sides = set(), set()
    makers_side = ""
    for sub_trade in sub_trades:
        if sub_trade.is_maker:
            makers_side = sub_trade.side
            makers_price_list.add(sub_trade.trade.price)
    if makers_side:
        sides.add(makers_side)
    # makers_price_list = list(makers_price_list)
    price_set = makers_price_list.copy()
    if new_order.price:
        sides.add(new_order.side)
        price_set.add(new_order.price)
    new_order_book = models.Order.get_order_book(
        db=db,
        symbol=new_order.symbol,
        sides=list(sides),
        price_list=list(price_set),
    )
    order_book_updates = []
    for order in new_order_book:
        order_book_out = schemas.OrderBookOut.from_orm(order)
        order_book_updates.append(order_book_out)
        price_set.remove(order_book_out.price)
    for price in price_set:
        if price in makers_price_list:
            side = makers_side
        else:
            side = new_order.side
        order_book_updates.append(schemas.OrderBookOut(
            side=side,
            quantity=Decimal('0.0'),
            price=price
        ))
    return order_book_updates


def cancel_order(db: Session, order: models.Order, records: dict) -> dict:
    if order.status in enums.OrderStatus.open_orders.value:
        if order.locked_asset == enums.CollateralType.asset.value:
            balance = models.Balance.unlock(
                info={
                    "account_id": order.account_id,
                    "asset": enums.CollateralAsset.usdt.value,
                    "amount": order.locked_quantity
                },
                db=db
            )
            records['balances']['taker'] = [balance]
        else:
            position = models.Position.unlock(
                info={
                    "account_id": order.account_id,
                    "symbol": order.symbol,
                    "amount": order.locked_quantity,
                    "side": order.side,
                },
                db=db
            )
            records['positions'].append(position)
        order.status = enums.OrderStatus.canceled.value
        order.locked_quantity -= order.locked_quantity
        db.commit()
    return records


def match_order(db: Session, order: models.Order, records: dict, offset: int = 0) -> dict:
    if order.post_only:
        order.status = enums.OrderStatus.placed.value
        records['orders'].append(order)
        return records
    if order.side == enums.OrderSide.long.value:
        opposite_side = enums.OrderSide.short.value
        price_order_by = models.Order.price.asc()
    else:
        opposite_side = enums.OrderSide.long.value
        price_order_by = models.Order.price.desc()
    maker_orders_query = [
        models.Order.status.in_(enums.OrderStatus.active_orders.value),
        models.Order.symbol == order.symbol,
        models.Order.side == opposite_side,
    ]
    if order.type == enums.OrderType.limit.value:
        if order.side == enums.OrderSide.long.value:
            maker_orders_query.append(models.Order.price <= order.price)
        else:
            maker_orders_query.append(models.Order.price >= order.price)
    maker_orders = db.query(models.Order).filter(
        *maker_orders_query
    ).order_by(
        price_order_by,
        models.Order.insert_time.desc()
    ).offset(offset=offset).limit(10)
    if maker_orders.count() > 0:
        for maker_order in maker_orders:
            trade = models.Trade.create_trade(
                db=db,
                maker=maker_order,
                taker=order,
            )
            sub_trades, balances, positions = models.SubTrade.create_sub_trades(
                db, trade)
            records['orders'].append(maker_order)
            records['trades'].append(trade)
            records['sub_trades'] += sub_trades
            records['balances']['makers'] += balances['maker']
            records['balances']['taker'] = balances['taker']
            records['positions'] += positions
            if order.status == enums.OrderStatus.filled.value:
                return records
        return match_order(db=db, order=order, records=records, offset=offset+1)
    if order.type == enums.OrderType.limit.value and order.status == enums.OrderStatus.queued.value:
        order.status = enums.OrderStatus.placed.value
    return records


def publish_new_events(new_events: dict, symbol: str):
    for order in new_events['orders']:
        order_out = schemas.OrderOut.from_orm(order)
        order_out.publish(enums.EventType.update_order.value)
    for sub_trade in new_events['sub_trades']:
        order = sub_trade.trade.maker_order if sub_trade.is_maker else sub_trade.trade.taker_order
        sub_trade_out = schemas.SubTradeOut(
            id=sub_trade.id,
            order_id=order.id,
            account_id=order.account_id,
            symbol=symbol,
            price=sub_trade.trade.price,
            quantity=sub_trade.trade.quantity,
            quote_quantity=sub_trade.trade.quote_quantity,
            commission=sub_trade.commission,
            commission_asset=sub_trade.commission_asset,
            side=sub_trade.side,
            is_maker=sub_trade.is_maker,
            insert_time=sub_trade.trade.insert_time,
        )
        sub_trade_out.publish(event_type=enums.EventType.sub_trade.value)
    for trade in new_events['trades']:
        public_trade = schemas.PublicTrade.from_orm(trade)
        public_trade.symbol = symbol
        public_trade.publish(event_type=enums.EventType.trade.value)
    for order_book_update in new_events['order_book_updates']:
        order_book_update.publish(
            event_type=enums.EventType.order_book.value,
            symbol=symbol,
        )
    balances = new_events['balances']['makers'] + \
        new_events['balances']['taker']
    for balance in balances:
        schemas.BalanceOut.from_orm(balance).publish(
            event_type=enums.EventType.balance.value
        )
    for position in new_events['positions']:
        schemas.PositionOut.from_orm(position).publish(
            event_type=enums.EventType.position.value
        )
