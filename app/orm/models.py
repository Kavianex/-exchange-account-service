from sqlalchemy import DECIMAL, INTEGER, Boolean, Column, ForeignKey, String, UniqueConstraint, TIMESTAMP, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Session, exc
from sqlalchemy.sql import func, text
from decimal import Decimal
import uuid
import math
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
    chain_id = Column(String, unique=True, index=True)
    chain_hex = Column(String)
    symbol = Column(String)
    block_explorer_url = Column(String)
    last_updated_block = Column(Integer)
    confirmations = Column(Integer)


class Asset(Base):
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    standard = Column(String, ForeignKey("networks.standard"))
    network = relationship("Network", foreign_keys=[standard])
    symbol = Column(String, unique=True, index=True)
    name = Column(String)
    digits = Column(Integer, default=18)
    status = Column(String, default=enums.AssetStatus.active.value)
    contract_address = Column(String)


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String, index=True, unique=True)
    base_asset = Column(String)
    quote_asset = Column(String, ForeignKey("assets.symbol"))
    quote = relationship("Asset", foreign_keys=[quote_asset])
    base_precision = Column(Integer)
    quote_precision = Column(Integer)
    min_base_quantity = Column(DECIMAL(20, 18))
    min_quote_quantity = Column(DECIMAL(20, 18))
    status = Column(String)
    margin_pool = Column(DECIMAL(20, 18), default=Decimal('0.0'))
    open_interest = Column(DECIMAL(20, 18), default=Decimal('0.0'))


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    address = Column(String, unique=True, index=True)
    chain_id = Column(String, ForeignKey("networks.chain_id"))
    network = relationship("Network", foreign_keys=[chain_id])
    referral_code = Column(String)
    referred_wallet = Column(String, nullable=True)
    __table_args__ = (UniqueConstraint(
        'address', 'chain_id', name='_address_standard_uc'),)

    @staticmethod
    def generate_referral_code(k: int = 6):
        return uuid.uuid4().hex[:k]


class Broker(Base):
    __tablename__ = "brokers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallets.id"))
    wallet = relationship("Wallet", foreign_keys=[wallet_id])
    name = Column(String)


class Account(Base):
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallets.id"))
    wallet = relationship("Wallet", foreign_keys=[wallet_id])
    broker_id = Column(UUID(as_uuid=True), ForeignKey("brokers.id"))
    broker = relationship("Broker", foreign_keys=[broker_id])
    type = Column(String)
    leverage = Column(INTEGER, default=5)


class Balance(Base):
    __tablename__ = "balances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"))
    account = relationship("Account", foreign_keys=[account_id])
    asset = Column(String)
    free = Column(DECIMAL, default=Decimal('0.0'))
    locked = Column(DECIMAL, default=Decimal('0.0'))

    @classmethod
    def get_lock_amount(cls, amount):
        max_digits = 3
        digit_factor = Decimal(str(10 ** max_digits))
        amount *= digit_factor
        amount = math.ceil(amount)
        amount /= digit_factor
        return amount

    @classmethod
    def lock(cls, info: dict, db: Session):
        try:
            db_balance = db.query(cls).filter(
                cls.account_id == info['account_id'],
                cls.asset == enums.CollateralAsset.usdt.value
            ).with_for_update().one()
            lock_amount = cls.get_lock_amount(info['amount'])
            if db_balance.free >= lock_amount:
                db_balance.locked += lock_amount
                db_balance.free -= lock_amount
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
            lock_amount = cls.get_lock_amount(info['amount'])
            if db_balance.locked >= lock_amount:
                db_balance.free += lock_amount
                db_balance.locked -= lock_amount
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
    def exchange(cls, db: Session, account_id: uuid.UUID, collateral: dict) -> bool:
        asset = db.query(cls).filter(
            cls.account_id == account_id,
            cls.asset == collateral['asset']
        ).with_for_update().one()
        _locked = collateral['locked']
        _free = collateral['free']
        _rebate = collateral['rebate']
        if asset.locked >= _locked:
            asset.locked -= _locked
        else:
            raise
        asset.free += _free
        asset.free += collateral['rebate']
        print(
            f"free+: {_free}, locked-: {_locked}, rebate: {_rebate}")
        db.add(asset)
        return [asset]


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"))
    account = relationship("Account", foreign_keys=[account_id])
    symbol = Column(String, ForeignKey("contracts.symbol"))
    contract = relationship("Contract", foreign_keys=[symbol])
    base = Column(String)
    quote = Column(String)
    side = Column(String)
    position_mode = Column(String)
    type = Column(String)
    status = Column(String, default=enums.OrderStatus.queued.value)
    price = Column(DECIMAL, default=Decimal('0.0'))
    quantity = Column(DECIMAL, default=Decimal('0.0'))
    quote_quantity = Column(DECIMAL, default=Decimal('0.0'))
    filled_quantity = Column(DECIMAL, default=Decimal('0.0'))
    filled_quote = Column(DECIMAL, default=Decimal('0.0'))
    leverage = Column(INTEGER)
    post_only = Column(Boolean, default=False)
    reduce_only = Column(Boolean, default=False)
    locked_asset = Column(String)
    locked_quantity = Column(DECIMAL, default=Decimal('0.0'))
    insert_time = Column(TIMESTAMP, server_default=func.now())
    update_time = Column(TIMESTAMP, server_default=func.now(),
                         onupdate=func.current_timestamp())

    def lock_balance(self, db: Session) -> Balance:
        collateral = self._get_collateral()
        if self.reduce_only:
            locked_balance = Position.lock(info=collateral, db=db)
        else:
            locked_balance = Balance.lock(info=collateral, db=db)
        self.locked_asset = collateral['collateral_type']
        self.locked_quantity = collateral['amount']
        return locked_balance

    def _get_collateral(self):
        if self.reduce_only:
            amount = self.quantity
            collateral_type = enums.CollateralType.position.value
        else:
            if self.type == enums.OrderType.limit.value:
                order_value = self.quantity * self.price
            elif self.type == enums.OrderType.market.value:
                order_value = self.quote_quantity
            else:
                raise
            collateral_type = enums.CollateralType.asset.value
            amount = order_value / self.leverage
            if not self.post_only:
                fee = order_value * settings.FEES[enums.OrderRole.taker.value]
                amount += fee
        collateral = {
            "amount": amount,
            "collateral_type": collateral_type,
            "account_id": self.account_id,
            "order_side": self.side,
            "position_mode": self.position_mode,
        }
        return collateral

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
            sides = [enums.OrderSide.long.value, enums.OrderSide.short.value]
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
    def create_trade(cls, db: Session, maker: Order, taker: Order, contract: Contract) -> bool:
        active_maker_quantity = maker.quantity - maker.filled_quantity
        if taker.quantity:
            taker_remained_quantity = taker.quantity - taker.filled_quantity
            trade_quantity = min(taker_remained_quantity,
                                 active_maker_quantity)
        else:
            taker_remained_quote_quantity = taker.quote_quantity - taker.filled_quote
            if active_maker_quantity * maker.price <= taker_remained_quote_quantity:
                trade_quantity = active_maker_quantity
            else:
                # TODO: quantity decimal
                trade_quantity = taker_remained_quote_quantity / maker.price
        lot_step = int(trade_quantity / contract.min_base_quantity)
        trade_quantity = lot_step * contract.min_base_quantity
        trade_quote_quantity = trade_quantity * maker.price
        if trade_quantity == Decimal('0.0'):
            if taker.filled_quantity > Decimal('0.0'):
                taker.status = enums.OrderStatus.filled.value
            else:
                taker.status = enums.OrderStatus.canceled.value
            trade = None
        else:
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
        positions = []
        # contract = db.query(Contract).filter(
        #     Contract.symbol == trade.maker_order.symbol,
        # ).with_for_update().one()
        open_interest = Decimal('0.0')
        for idx, order in enumerate([trade.maker_order, trade.taker_order]):
            is_maker = idx == 0
            order.filled_quantity += trade.quantity
            order.filled_quote += trade.quote_quantity
            trade_fee = settings.FEES[enums.OrderRole.maker.value if is_maker else enums.OrderRole.taker.value]
            trade_commission = trade.quote_quantity * trade_fee
            trade_rebate = Decimal('0.0')
            if trade_commission < Decimal('0.0'):
                trade_rebate = -1 * trade_commission
                trade_commission = Decimal('0.0')

            position = Position.get_order_position(db=db, order=order)
            # position_margin = position.margin
            margin_to_free_balance = Decimal('0.0')
            locked_balance_to_margin = Decimal('0.0')
            locked_balance_to_free_balance = Decimal('0.0')
            # locked2margin_quote_balance_change = Decimal('0.0')
            if position.side == order.side:
                # increase position size by order on the same size
                transfering_collateral_dir = enums.PositionMarginAction.add_to_margin.value
                position.quantity += trade.quantity
                open_interest += trade.quantity
                margin_change_quantity = trade.quote_quantity / order.leverage
                # contract.margin_pool += margin_change_quantity
                position.margin += margin_change_quantity
                locked_balance_to_margin = margin_change_quantity + trade_commission
            else:
                # decrease position size by order on the opposite site
                transfering_collateral_dir = enums.PositionMarginAction.take_from_margin.value
                open_interest -= trade.quantity
                max_lowering_quantity = min(position.quantity, trade.quantity)
                position.quantity -= max_lowering_quantity
                margin_change_quantity = max_lowering_quantity * \
                    position.entry_price / order.leverage
                # margin_to_free_balance = margin_change_quantity
                lowering_quote_quantity = max_lowering_quantity * trade.price / order.leverage
                if order.locked_asset == enums.CollateralType.asset.value:
                    locked_balance_to_free_balance += lowering_quote_quantity
                pnl = (lowering_quote_quantity -
                       margin_change_quantity) * position.leverage
                if position.side == enums.OrderSide.short.value:
                    pnl *= -1
                margin_to_free_balance += pnl + margin_change_quantity
                margin_to_free_balance -= trade_commission
                # contract.margin_pool -= margin_change_quantity
                position.margin -= margin_change_quantity
                remained_quantity = trade.quantity - max_lowering_quantity
                if remained_quantity > Decimal('0.0'):
                    position.side = order.side
                    position.quantity = remained_quantity
                    margin_change_quantity = remained_quantity * trade.price / order.leverage
                    # contract.margin_pool += margin_change_quantity
                    position.margin += margin_change_quantity
                    locked_balance_to_margin += margin_change_quantity + trade_commission

            if position.quantity == Decimal('0.0'):
                position.entry_price = Decimal('0.0')
                # margin_to_free_balance += position.margin
                position.margin = Decimal('0.0')
            else:
                position.entry_price = position.margin * position.leverage / position.quantity

            liquidation_price_change = position.entry_price / \
                Decimal(str(position.leverage))
            commission_factor = 1 - settings.FEES[enums.OrderRole.taker.value]
            if position.side == enums.OrderSide.long.value:
                liquidation_price_change *= -1
                commission_factor = 1 + \
                    settings.FEES[enums.OrderRole.taker.value]
            commission_factor = Decimal('1.0')
            position.liquidation_price = position.entry_price + liquidation_price_change
            position.liquidation_price *= commission_factor

            margin_change_quantity = trade.quote_quantity / order.leverage
            if transfering_collateral_dir == enums.PositionMarginAction.add_to_margin.value:
                if order.locked_asset == enums.CollateralType.asset.value:
                    order.locked_quantity -= margin_change_quantity
                    order.locked_quantity -= trade_commission
                else:
                    raise
            elif transfering_collateral_dir == enums.PositionMarginAction.take_from_margin.value:
                if order.locked_asset == enums.CollateralType.asset.value:
                    order.locked_quantity -= margin_change_quantity
                else:
                    position.locked_quantity -= trade.quantity
                    order.locked_quantity -= trade.quantity
                # margin_to_free_balance -= trade_commission
            if order.status == enums.OrderStatus.filled.value:
                if order.locked_asset == enums.CollateralType.asset.value:
                    locked_balance_to_free_balance += order.locked_quantity
                    order.locked_quantity = Decimal('0.0')

            # margin_to_free_balance -= trade_commission
            free = margin_to_free_balance + locked_balance_to_free_balance
            unlocked = locked_balance_to_margin + locked_balance_to_free_balance

            updated_balances = Balance.exchange(
                db=db,
                account_id=order.account_id,
                collateral={
                    "locked": unlocked,
                    "free": free,
                    "asset": enums.CollateralAsset.usdt.value,
                    "rebate": trade_rebate
                },
            )
            balances['maker' if is_maker else 'taker'] = updated_balances
            sub_trades.append(
                SubTrade(
                    trade=trade,
                    commission=trade_commission,
                    commission_asset=enums.CollateralAsset.usdt.value,
                    side=order.side,
                    is_maker=is_maker,
                )
            )
            positions.append(position)
        # contract.open_interest += open_interest / Decimal('2.0')
        # db.add(contract)
        db.add_all(sub_trades)
        db.add_all(positions)
        for sub_trade in sub_trades:
            if sub_trade.commission > Decimal('0.0'):
                ExchangeIncome.pay_commissions(db=db, sub_trade=sub_trade)
        return sub_trades, balances, positions


class Position(Base):
    __tablename__ = "positions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"))
    account = relationship("Account", foreign_keys=[account_id])
    symbol = Column(String, ForeignKey("contracts.symbol"))
    contract = relationship("Contract", foreign_keys=[symbol])
    side = Column(String)
    quantity = Column(DECIMAL, default=Decimal('0.0'))
    locked_quantity = Column(DECIMAL, default=Decimal('0.0'))
    entry_price = Column(DECIMAL, default=Decimal('0.0'))
    liquidation_price = Column(DECIMAL, default=Decimal('0.0'))
    # un_realized_profit =
    leverage = Column(INTEGER)
    margin = Column(DECIMAL, default=Decimal('0.0'))
    margin_type = Column(String, default=enums.MarginType.isolated.value)
    position_mode = Column(String, default=enums.PositionMode.ony_way.value)

    @property
    def size(self):
        if self.side == enums.OrderSide.long.value:
            _size = self.quantity
        else:
            _size = -self.quantity
        return _size

    @classmethod
    def lock(cls, info: dict, db: Session):
        try:
            db_position = db.query(cls).filter(
                cls.account_id == info['account_id'],
                cls.symbol == info['symbol'],
                # cls.position_mode == enums.PositionMode.ony_way.value,
                cls.side == enums.OrderSide.long.value if info[
                    'side'] == enums.OrderSide.short.value else enums.OrderSide.short.value,
            ).with_for_update().one()
            if db_position.quantity - db_position.locked_quantity >= info['amount'] > 0:
                db_position.locked_quantity += info['amount']
                return db_position
        except exc.NoResultFound:
            pass
        return None

    @classmethod
    def unlock(cls, info: dict, db: Session):
        try:
            db_position = db.query(cls).filter(
                cls.account_id == info['account_id'],
                cls.symbol == info['symbol'],
                # cls.position_mode == enums.PositionMode.ony_way.value,
                cls.side == enums.OrderSide.long.value if info[
                    'side'] == enums.OrderSide.short.value else enums.OrderSide.short.value,
            ).with_for_update().one()
            if db_position.side == enums.OrderSide.long.value:
                if db_position.quantity - db_position.locked_quantity >= info['amount'] > 0:
                    db_position.locked_quantity += info['amount']
                    return db_position
            elif db_position.side == enums.OrderSide.short.value:
                if db_position.quantity - db_position.locked_quantity <= -1 * info['amount'] < 0:
                    db_position.locked_quantity -= info['amount']
                    return db_position
            else:
                pass
        except exc.NoResultFound:
            pass
        return None

    @classmethod
    def get_open_positions(cls, account_id, db):
        return db.query(cls).filter(
            cls.account_id == account_id,
            cls.margin > Decimal('0.0'),
        ).order_by(
            cls.margin.desc()
        ).all()

    @classmethod
    def get_order_position(cls, db: Session, order: Order):
        try:
            position = db.query(Position).filter(
                Position.account_id == order.account_id,
                Position.symbol == order.symbol,
                Position.position_mode == enums.PositionMode.ony_way.value,
            ).with_for_update().one()
        except Exception as e:
            position = Position(
                account_id=order.account_id,
                symbol=order.symbol,
                position_mode=enums.PositionMode.ony_way.value,
                leverage=order.leverage,
                side=order.side,
                quantity=Decimal('0.0'),
                margin=Decimal('0.0'),
            )
            db.add(position)
        return position


class ExchangeIncome(Base):
    __tablename__ = "exchangeincomes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subtrade_id = Column(UUID(as_uuid=True), ForeignKey("subtrades.id"))
    subtrade = relationship("SubTrade", foreign_keys=[subtrade_id])
    commission = Column(DECIMAL, default=Decimal('0.0'))
    commission_asset = Column(String)
    exchange_income = Column(DECIMAL, default=Decimal('0.0'))
    broker_income = Column(DECIMAL, default=Decimal('0.0'))
    referral_income = Column(DECIMAL, default=Decimal('0.0'))

    @classmethod
    def pay_commissions(cls, db: Session, sub_trade: SubTrade):
        pass
        # commission = sub_trade.commission
        # income = cls(
        #     subtrade_id=sub_trade.id,
        #     commission=commission,
        #     commission_asset=sub_trade.commission_asset,
        #     exchange_income=,
        #     broker_income=,
        #     referral_income=,
        # )


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String, ForeignKey("assets.symbol"))
    asset = relationship("Asset", foreign_keys=[symbol])
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"))
    account = relationship("Account", foreign_keys=[account_id])
    blockNumber = Column(String)
    from_address = Column(String, unique=True, index=True)
    to_address = Column(String, unique=True, index=True)
    tx_hash = Column(String, unique=True, index=True)
    tx_input = Column(String, unique=True, index=True)
    nonce = Column(String, unique=True, index=True)
    index = Column(String, unique=True, index=True)
    value = Column(String, unique=True, index=True)
    action = Column(String, unique=True, index=True)
