from enum import Enum


class AssetStatus(Enum):
    active = "ACTIVE"
    deactive = "DEACTIVE"


class CollateralAsset(Enum):
    usdt = "USDT"


class CollateralType(Enum):
    asset = "ASSET"
    position = "POSITION"


class MarginType(Enum):
    isolated = "ISOLATED"


class PositionMode(Enum):
    ony_way = "ONE_WAY"
    hedge_mode = "HEDGE_MODE"


class ContractStatus(Enum):
    trading = "TRADING"
    stopped = "STOPPED"


class Roles(Enum):
    admin = 'ADMIN'
    staff = 'STAFF'
    user = 'USER'
    visitor = 'VISITOR'
    service = 'SERVICE'


class AccountType(Enum):
    main = "MAIN"
    sub = "SUB"


class OrderType(Enum):
    limit = "LIMIT"
    market = "MARKET"


class OrderSide(Enum):
    long = "LONG"
    short = "SHORT"


class OrderStatus(Enum):
    queued = "QUEUED"
    placed = "PLACED"
    # partial_filled = "PARTIAL_FIILED"
    filled = "FILLED"
    canceled = "CANCELED"
    open_orders = [queued, placed]
    active_orders = [placed]
    matched_orders = [placed, filled]


class ApplicationMode(Enum):
    production = "PRODUCTION"
    testnet = "TEST"


class NetworkChainIds(Enum):
    production = ["0x1"]
    testnet = ["0x5"]


class OrderRole(Enum):
    maker = "MAKER"
    taker = "TAKER"


class PositionMarginAction(Enum):
    add_to_margin = "ADD_T0_MARGIN"
    take_from_margin = "TAKE_FORM_MARGIN"


# class KafkaQueue(Enum):
#     match_engine = "MATCH_ENGINE"
#     account = "ACCOUNT"
#     public = "PUBLIC"


class QueueName(Enum):
    match_engine = "MATCH_ENGINE"
    publish = "PUBLISH"
    blockchain = "BLOCKCHAIN"
    # public = "PUBLIC"


class EeventTopic(Enum):
    order_update = "OrderUpdate"
    trade = "trade"
    account_trade = "accountTrade"
    balance = "balance"
    position = "position"
    order_book = "orderBook"


class EventType(Enum):
    send_order = "SEND_ORDER"
    cancel_order = "CANCEL_ORDER"
    update_order = "UPDATE_ORDER"
    trade = "TRADE"
    sub_trade = "SUB_TRADE"
    balance = "BALANCE"
    position = "POSITION"
    order_book = "ORDER_BOOK"
