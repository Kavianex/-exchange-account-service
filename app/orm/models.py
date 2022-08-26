from sqlalchemy import DECIMAL, INTEGER, Boolean, Column, ForeignKey, String, UniqueConstraint, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Session, exc
from sqlalchemy.sql import func
from decimal import Decimal
from uuid import uuid4
from internal import enums, schemas
from .database import Base


class Network(Base):
    __tablename__ = "networks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String)
    standard = Column(String, unique=True, index=True)
    address = Column(String)
    rpc_url = Column(String)
    chain_id = Column(INTEGER)
    chain_hex = Column(String)
    symbol = Column(String)
    block_explorer_url = Column(String)


class Crypto(Base):
    __tablename__ = "cryptos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    symbol = Column(String)
    name = Column(String)
    standard = Column(String, ForeignKey("networks.standard"))
    network = relationship("Network", foreign_keys=[standard])
    kind = Column(String)
    contract = Column(String, nullable=True)
    digits = Column(INTEGER)


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    address = Column(String, unique=True, index=True)
    standard = Column(String, ForeignKey("networks.standard"))
    network = relationship("Network", foreign_keys=[standard])
    referral_code = Column(String)
    referred_wallet = Column(String, nullable=True)
    __table_args__ = (UniqueConstraint(
        'address', 'standard', name='_address_standard_uc'),)

    @staticmethod
    def generate_referral_code(k: int = 6):
        return uuid4().hex[:k]


class Account(Base):
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallets.id"))
    wallet = relationship("Wallet", foreign_keys=[wallet_id])
    name = Column(String)
    type = Column(String)


class Balance(Base):
    __tablename__ = "balances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"))
    account = relationship("Account", foreign_keys=[account_id])
    asset = Column(String)
    free = Column(DECIMAL, default=Decimal('0.0'))
    locked = Column(DECIMAL, default=Decimal('0.0'))

    @classmethod
    def lock(cls, info: dict, db: Session):
        try:
            db_balance = db.query(cls).filter(
                cls.account_id == info['account_id'],
                cls.asset == info['asset']
            ).with_for_update().one()
            if db_balance.free >= info['amount']:
                db_balance.locked += info['amount']
                db_balance.free -= info['amount']
                return db_balance
        except exc.NoResultFound:
            pass
        return None

    @classmethod
    def update_or_create(cls, balance_in: schemas.BalanceIn, db: Session):
        db_balance = cls._update(balance_in=balance_in, db=db)
        if not db_balance:
            db_balance = cls._create(balance_in=balance_in, db=db)
        return db_balance

    @classmethod
    def _update(cls, balance_in: schemas.BalanceIn, db: Session):
        try:
            db_balance = db.query(cls).filter(
                cls.account_id == balance_in.account_id,
                cls.asset == balance_in.asset,
            ).with_for_update().one()
        except exc.NoResultFound:
            db_balance = None
        if db_balance:
            db_balance.free = balance_in.free
            db_balance.locked = balance_in.locked
            db.commit()
            db.refresh(db_balance)
        return db_balance

    @classmethod
    def _create(cls, balance_in: schemas.BalanceIn, db: Session):
        db_balance = cls(**balance_in.dict())
        db.add(db_balance)
        db.commit()
        db.refresh(db_balance)
        return db_balance


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"))
    account = relationship("Account", foreign_keys=[account_id])
    symbol = Column(String)
    base = Column(String)
    quote = Column(String)
    side = Column(String)
    type = Column(String)
    status = Column(String, default=enums.OrderStatus.queued.value)
    price = Column(DECIMAL, default=Decimal('0.0'))
    quantity = Column(DECIMAL, default=Decimal('0.0'))
    quote_quantity = Column(DECIMAL, default=Decimal('0.0'))
    filled_quantity = Column(DECIMAL, default=Decimal('0.0'))
    filled_quote = Column(DECIMAL, default=Decimal('0.0'))
    locked_asset = Column(String)
    locked_quantity = Column(DECIMAL, default=Decimal('0.0'))
    insert_time = Column(TIMESTAMP, server_default=func.now())
    update_time = Column(TIMESTAMP, server_default=func.now(),
                         onupdate=func.current_timestamp())

    def lock_balance(self, db: Session) -> Balance:
        lock_info = self._get_lock()
        lock_info['account_id'] = self.account_id
        locked_balance = Balance.lock(info=lock_info, db=db)
        self.locked_asset = lock_info['asset']
        self.locked_quantity = lock_info['amount']
        return locked_balance

    def _get_lock(self):
        if self.side == enums.OrderSide.buy.value:
            lock = {
                "asset": self.quote
            }
            if self.type == enums.OrderType.limit.value:
                lock['amount'] = self.quantity * self.price
            elif self.type == enums.OrderType.market.value:
                lock['amount'] = self.quote_quantity
        else:
            lock = {
                "asset": self.base,
                "amount": self.quantity
            }
        return lock


class Trade(Base):
    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    maker_order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"))
    maker_order = relationship("Order", foreign_keys=[maker_order_id])
    taker_order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"))
    taker_order = relationship("Order", foreign_keys=[taker_order_id])
    quantity = Column(DECIMAL, default=Decimal('0.0'))
    price = Column(DECIMAL, default=Decimal('0.0'))
    quote_quantity = Column(DECIMAL, default=Decimal('0.0'))
    insert_time = Column(TIMESTAMP, server_default=func.now())


class SubTrade(Base):
    __tablename__ = "subtrades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    trade_id = Column(UUID(as_uuid=True), ForeignKey("trades.id"))
    trade = relationship("Trade", foreign_keys=[trade_id])
    commission = Column(DECIMAL, default=Decimal('0.0'))
    commission_asset = Column(String)
    side = Column(String)
    is_maker = Column(Boolean)
