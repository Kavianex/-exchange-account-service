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
    partial_filled = "PARTIAL_FIILED"
    filled = "FILLED"
    canceled = "CANCELED"
