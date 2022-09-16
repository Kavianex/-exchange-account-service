from enum import Enum


class Roles(Enum):
    admin = 'ADMIN'
    staff = 'STAFF'
    user = 'USER'
    visitor = 'VISITOR'
    service = 'SERVICE'


class CryptoKind(Enum):
    coin = "COIN"
    token = "TOKEN"


class AccountType(Enum):
    main = "MAIN"
    sub = "SUB"


class OrderType(Enum):
    limit = "LIMIT"
    market = "MARKET"


class OrderSide(Enum):
    buy = "BUY"
    sell = "SELL"


class OrderStatus(Enum):
    queued = "QUEUED"
    placed = "PLACED"
    # partial_filled = "PARTIAL_FIILED"
    filled = "FILLED"
    canceled = "CANCELED"
    open_orders = [queued, placed]
    active_orders = [placed]
    matched_orders = [placed, filled]


class OrderRole(Enum):
    maker = "MAKER"
    taker = "TAKER"


class KafkaQueue(Enum):
    match_engine = "MATCH_ENGINE"
    account = "ACCOUNT"
    public = "PUBLIC"


class EeventTopic(Enum):
    order_update = "OrderUpdate"
    trade = "trade"
    account_trade = "accountTrade"
    balance = "balance"
    order_book = "orderBook"


class EventType(Enum):
    send_order = "SEND_ORDER"
    cancel_order = "CANCEL_ORDER"
    update_order = "UPDATE_ORDER"
    trade = "TRADE"
    sub_trade = "SUB_TRADE"
    balance = "BALANCE"
    order_book = "ORDER_BOOK"
