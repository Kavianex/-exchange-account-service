from sqlalchemy import DECIMAL, INTEGER, Boolean, Column, ForeignKey, String, UniqueConstraint, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Session, exc
from sqlalchemy.sql import func, text
from decimal import Decimal
import uuid
import settings
from internal import enums, schemas
from .database import Base


class Network(Base):
    __tablename__ = "networks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String)
    name = Column(String)
    standard = Column(String, ForeignKey("networks.standard"))
    network = relationship("Network", foreign_keys=[standard])
    kind = Column(String)
    contract = Column(String, nullable=True)
    digits = Column(INTEGER)


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    address = Column(String, unique=True, index=True)
    standard = Column(String, ForeignKey("networks.standard"))
    network = relationship("Network", foreign_keys=[standard])
    referral_code = Column(String)
    referred_wallet = Column(String, nullable=True)
    __table_args__ = (UniqueConstraint(
        'address', 'standard', name='_address_standard_uc'),)

    @staticmethod
    def generate_referral_code(k: int = 6):
        return uuid.uuid4().hex[:k]


class Account(Base):
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallets.id"))
    wallet = relationship("Wallet", foreign_keys=[wallet_id])
    name = Column(String)
    type = Column(String)


class Balance(Base):
    __tablename__ = "balances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    def unlock(cls, info: dict, db: Session):
        try:
            db_balance = db.query(cls).filter(
                cls.account_id == info['account_id'],
                cls.asset == info['asset']
            ).with_for_update().one()
            if db_balance.locked >= info['amount']:
                db_balance.free += info['amount']
                db_balance.locked -= info['amount']
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

    @classmethod
    def exchange(cls, db: Session, account_id: uuid.UUID, pay: dict, get: dict) -> bool:
        pay_asset = db.query(cls).filter(
            cls.account_id == account_id,
            cls.asset == pay['asset']
        ).with_for_update().first()
        if not pay_asset:
            return False
        pay_amount = pay['amount']
        if pay_asset.locked >= pay_amount:
            pay_asset.locked -= pay_amount
            pay_asset.free += pay['rebate']
        get_amount = get['amount']
        get_asset = db.query(cls).filter(
            cls.account_id == account_id,
            cls.asset == get['asset']
        ).with_for_update().first()
        if not get_asset:
            get_asset = cls(account_id=account_id, asset=get['asset'])
        get_asset.free += get_amount
        db.add(get_asset)
        return [pay_asset, get_asset]


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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

    @classmethod
    def filter_open_orders(cls, db: Session, account_id: uuid.UUID, symbol: str = ""):
        query = [
            cls.status.in_(enums.OrderStatus.open_orders.value),
            cls.account_id == account_id
        ]
        if symbol:
            query.append(cls.symbol == symbol)
        return db.query(cls).filter(*query).all()

    @classmethod
    def get_order_book(cls, db: Session, symbol: str = "", sides: list = [], price_list: list[Decimal] = []):
        if not sides:
            sides = [enums.OrderSide.buy.value, enums.OrderSide.sell.value]
        query = """
            select 
            price, 
            side,
            sum(quantity - filled_quantity) as quantity 
            from orders
            where symbol = :symbol and side = ANY(:sides) {}
            and status = ANY(:status)
            group by price, side
            order by  price desc, side desc
        """
        price_list_filter = ""
        query_params = {
            'symbol': symbol,
            'status': enums.OrderStatus.active_orders.value,
            "sides": sides,
        }
        if price_list:
            price_list_filter = f"and price = ANY(:price_list)"
            query_params['price_list'] = price_list
        return db.execute(
            text(query.format(price_list_filter)),
            query_params
        ).all()


class Trade(Base):
    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    maker_order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"))
    maker_order = relationship("Order", foreign_keys=[maker_order_id])
    taker_order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"))
    taker_order = relationship("Order", foreign_keys=[taker_order_id])
    quantity = Column(DECIMAL, default=Decimal('0.0'))
    price = Column(DECIMAL, default=Decimal('0.0'))
    quote_quantity = Column(DECIMAL, default=Decimal('0.0'))
    insert_time = Column(TIMESTAMP, server_default=func.now())

    @classmethod
    def create_trade(cls, db: Session, maker: Order, taker: Order) -> bool:
        active_maker_quantity = maker.quantity - maker.filled_quantity
        if taker.quantity:
            taker_remained_quantity = taker.quantity - taker.filled_quantity
            if active_maker_quantity <= taker_remained_quantity:
                trade_quantity = active_maker_quantity
            else:
                trade_quantity = taker_remained_quantity
        else:
            taker_remained_quote_quantity = taker.quote_quantity - taker.filled_quote
            if active_maker_quantity * maker.price <= taker_remained_quote_quantity:
                trade_quantity = active_maker_quantity
            else:
                trade_quantity = taker_remained_quote_quantity / maker.price
        trade_quote_quantity = trade_quantity * maker.price
        if trade_quantity == active_maker_quantity:
            maker.status = enums.OrderStatus.filled.value
        if taker.quantity:
            if taker_remained_quantity == trade_quantity:
                taker.status = enums.OrderStatus.filled.value
        else:
            if taker_remained_quote_quantity == trade_quote_quantity:
                taker.status = enums.OrderStatus.filled.value
        trade = cls(
            maker_order=maker,
            taker_order=taker,
            price=maker.price,
            quantity=trade_quantity,
            quote_quantity=trade_quote_quantity
        )
        db.add(trade)
        return trade


class SubTrade(Base):
    __tablename__ = "subtrades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trade_id = Column(UUID(as_uuid=True), ForeignKey("trades.id"))
    trade = relationship("Trade", foreign_keys=[trade_id])
    commission = Column(DECIMAL, default=Decimal('0.0'))
    commission_asset = Column(String)
    side = Column(String)
    is_maker = Column(Boolean)

    @classmethod
    def create_sub_trades(cls, db: Session, trade: Trade) -> list:
        sub_trades = []
        balances = {
            "taker": [],
            "maker": []
        }
        if trade.taker_order.side == enums.OrderSide.buy.value:
            taker_receive_amount = trade.quantity
        else:
            taker_receive_amount = trade.quote_quantity
        for idx, order in enumerate([trade.maker_order, trade.taker_order]):
            is_maker = idx == 0
            order.filled_quantity += trade.quantity
            order.filled_quote += trade.quote_quantity

            pay_amount = trade.quantity if order.side == enums.OrderSide.sell.value else trade.quote_quantity
            pay_asset = order.base if order.side == enums.OrderSide.sell.value else order.quote

            get_amount = trade.quote_quantity if order.side == enums.OrderSide.sell.value else trade.quantity
            get_asset = order.quote if order.side == enums.OrderSide.sell.value else order.base

            order.locked_quantity -= pay_amount
            trade_fee = settings.FEES[enums.OrderRole.maker.value if is_maker else enums.OrderRole.taker.value]
            trade_commission = taker_receive_amount * trade_fee
            trade_rebate = Decimal('0.0')
            if is_maker:
                trade_rebate = -1 * trade_commission
            else:
                get_amount -= trade_commission

            updated_balances = Balance.exchange(
                db=db,
                account_id=order.account_id,
                pay={
                    "amount": pay_amount,
                    "asset": pay_asset,
                    "rebate": trade_rebate
                },
                get={
                    "amount": get_amount,
                    "asset": get_asset,
                },
            )
            balances['maker' if is_maker else 'taker'] = updated_balances
            sub_trades.append(
                SubTrade(
                    trade=trade,
                    commission=trade_commission,
                    commission_asset=trade.maker_order.locked_asset,
                    side=order.side,
                    is_maker=is_maker,
                )
            )
        db.add_all(sub_trades)
        return sub_trades, balances
