from kafka import client as kafka_client
from datetime import datetime
from decimal import Decimal
import requests
import uuid
import pydantic
from orm import database, models
from . import enums
import settings


class PydanticBaseModel(pydantic.BaseModel):
    class Config:
        orm_mode = True
        use_enum_values = True

    def publish(self, event_type: enums.EventType, symbol: str = ""):
        kafka_client.publish(
            info=self,
            event_type=event_type,
            symbol=symbol,
        )

    def serialize(self):
        info = self.dict()
        for key, value in info.items():
            if isinstance(value, uuid.UUID):
                info[key] = str(value)
            elif isinstance(value, Decimal):
                info[key] = str(value)
            elif isinstance(value, datetime):
                info[key] = str(value)
        return info


class SignOut(PydanticBaseModel):
    wallet_address: str
    expire: int
    text2sign: str


class Asset(pydantic.BaseModel):
    symbol: pydantic.types.constr(
        min_length=2, max_length=10, strip_whitespace=True)
    name: pydantic.types.constr(min_length=5, max_length=80)
    digits: pydantic.types.conint(gt=2, lt=19)
    contract_address: pydantic.types.constr(
        min_length=2, max_length=64, strip_whitespace=True)
    standard: pydantic.types.constr(
        min_length=1, max_length=10, strip_whitespace=True)

    class Config:
        orm_mode = True
        use_enum_values = True

    @classmethod
    def get_asset(cls, symbol: str):
        db = next(database.get_db())
        asset = db.query(models.Asset).filter(
            models.Asset.symbol == symbol
        ).first()
        db.close()
        return asset


class AssetOut(Asset):
    status: enums.AssetStatus = enums.AssetStatus.active.value


class AssetIn(Asset):

    @pydantic.validator('symbol')
    def be_capital(cls, v):
        if not v == v.upper():
            raise ValueError("symbol must be upper case")
        return v

    @pydantic.validator('symbol')
    def unique_symbol(cls, v):
        db = database.SessionLocal()
        asset = db.query(models.Asset).filter(models.Asset.symbol == v).first()
        db.close()
        if asset:
            raise ValueError("symbol already exists!")
        return v


class Contract(pydantic.BaseModel):
    base_precision: pydantic.types.conint(ge=0)
    quote_precision: pydantic.types.conint(ge=0)
    base_asset: str
    quote_asset: str
    min_base_quantity: pydantic.types.confloat(gt=0)
    min_quote_quantity: pydantic.types.confloat(gt=0)

    class Config:
        orm_mode = True
        use_enum_values = True

    @classmethod
    def is_new(cls, base_asset: str, quote_asset: str) -> bool:
        db = database.SessionLocal()
        contract = db.query(models.Contract).filter(
            models.Contract.base_asset == base_asset,
            models.Contract.quote_asset == quote_asset,
        ).first()
        db.close()
        return contract is None


class ContractOut(Contract):
    symbol: str
    status: enums.ContractStatus
    margin_pool: Decimal
    open_interest: Decimal


class ContractIn(Contract):
    @pydantic.root_validator()
    def validate_precisions(cls, values):
        base_asset = values.get("base_asset", "")
        quote_asset = values.get("quote_asset", "")
        base_precision = values.get("base_precision")
        quote_precision = values.get("quote_precision")
        if not base_asset or not quote_asset or not base_precision or not quote_precision:
            return values
        base_precision = int(base_precision)
        quote_precision = int(quote_precision)
        # base_asset = Asset.get_asset(base_asset)
        # if base_asset.digits < base_precision:
        #     raise ValueError("base_precision is too big")
        quote_asset = Asset.get_asset(quote_asset)
        if quote_asset.digits < quote_precision:
            raise ValueError("quote_precision is too big")
        if quote_precision * base_precision > quote_asset.digits:
            raise ValueError(
                "quote_precision * base_precision can't be more than quote_asset.digits")
        if not cls.is_new(base_asset=base_asset, quote_asset=quote_asset.symbol):
            raise ValueError("symbol exsists")
        return values

    @pydantic.validator('quote_asset', allow_reuse=True)
    def check_asset(cls, v):
        if not v == "USDT":
            raise ValueError("invalid quote_asset!")
        return v


class Broker(PydanticBaseModel):
    wallet_id: pydantic.types.UUID4
    name: str

    class Config:
        orm_mode = True
        use_enum_values = True


class BrokerOut(Broker):
    id: pydantic.types.UUID4


class BrokerIn(Broker):
    pass


class Account(PydanticBaseModel):
    wallet_id: pydantic.types.UUID4
    type: enums.AccountType
    leverage: pydantic.conint(ge=1) = 5

    class Config:
        orm_mode = True
        use_enum_values = True


class AccountOut(Account):
    id: pydantic.types.UUID4


class AccountIn(Account):
    # leverage: pydantic.conint(ge=1) = 5
    pass


class Balance(PydanticBaseModel):
    asset: pydantic.types.constr(max_length=10)
    account_id: pydantic.types.UUID4

    # class Config:
    #     orm_mode = True
    #     use_enum_values = True


class BalanceOut(Balance):
    free: pydantic.condecimal(ge=Decimal('0.0')) = Decimal('0.0')
    locked: pydantic.condecimal(ge=Decimal('0.0')) = Decimal('0.0')


class BalanceIn(Balance):
    free: pydantic.condecimal(ge=Decimal('0.0'))
    locked: pydantic.condecimal(ge=Decimal('0.0'))

    @pydantic.validator('asset')
    def check_uppercase(cls, v):
        if not v == v.upper():
            raise ValueError("must be upper case")
        return v

    @pydantic.validator('account_id')
    def check_account_id(cls, v):
        db = database.SessionLocal()
        db_account = db.query(models.Account).filter(
            models.Account.id == v).first()
        if not db_account:
            raise ValueError("account_id does not exsit")
        return v


class Wallet(PydanticBaseModel):
    chain_id: pydantic.types.constr(min_length=3, max_length=10)

    class Config:
        orm_mode = True
        use_enum_values = True


class WalletOut(Wallet):
    id: pydantic.types.UUID4
    address: pydantic.types.constr(
        min_length=10, strip_whitespace=True, max_length=100)
    referral_code: pydantic.types.constr(max_length=10)
    referred_wallet: pydantic.types.constr(min_length=3, max_length=100) = None


class WalletIn(Wallet):
    referred_code: pydantic.types.constr(max_length=10) = None

    def is_valid(self, address):
        db = database.SessionLocal()
        print(address, self.chain_id)
        wallet = db.query(models.Wallet).filter(
            models.Wallet.chain_id == self.chain_id,
            models.Wallet.address == address,
        ).first()
        db.close()
        if wallet:
            return False
        return True

    @pydantic.validator('chain_id')
    def check_exist(cls, v):
        db = database.SessionLocal()
        network = db.query(models.Network).filter(
            models.Network.chain_id == v).first()
        db.close()
        if not network:
            raise ValueError('invalid chain_id for network.')
        return v


class Network(PydanticBaseModel):
    name: pydantic.types.constr(min_length=5)
    standard: pydantic.types.constr(min_length=3)
    rpc_url: pydantic.HttpUrl
    chain_id: pydantic.types.constr(min_length=1)
    chain_hex: pydantic.types.constr(min_length=3)
    symbol: pydantic.types.constr(min_length=2)
    block_explorer_url: pydantic.HttpUrl
    address: pydantic.types.constr(min_length=20, max_length=50)
    last_updated_block: pydantic.conint(gt=0)
    confirmations: pydantic.conint(gt=0)

    class Config:
        orm_mode = True
        use_enum_values = True


class NetworkOut(Network):
    pass


class NetworkIn(Network):
    @pydantic.validator("symbol")
    def unique_symbol(cls, v):
        db = database.SessionLocal()
        network = db.query(models.Network).filter(
            models.Network.symbol == v
        ).first()
        db.close()
        if network:
            raise ValueError("Network with this symbol already exsits!")
        return v

    @pydantic.validator("standard")
    def unique_standard(cls, v):
        db = database.SessionLocal()
        network = db.query(models.Network).filter(
            models.Network.standard == v
        ).first()
        db.close()
        if network:
            raise ValueError("Network with this standard already exsits!")
        return v

    @pydantic.validator("chain_id")
    def unique_chain_id(cls, v):
        db = database.SessionLocal()
        network = db.query(models.Network).filter(
            models.Network.chain_id == v
        ).first()
        db.close()
        if network:
            raise ValueError("Network with this chain_id already exsits!")
        return v

    @pydantic.validator("chain_hex")
    def unique_chain_hex(cls, v):
        db = database.SessionLocal()
        network = db.query(models.Network).filter(
            models.Network.chain_hex == v
        ).first()
        db.close()
        if network:
            raise ValueError("Network with this chain_hex already exsits!")
        return v


class Position(PydanticBaseModel):
    id: pydantic.types.UUID4
    account_id: pydantic.types.UUID4
    symbol: pydantic.constr(max_length=20)
    side: pydantic.constr(max_length=20)
    margin: pydantic.condecimal() = Decimal("0")
    leverage: int
    # size: int
    size: pydantic.condecimal() = Decimal("0")
    entry_price: pydantic.condecimal() = Decimal("0")
    liquidation_price: pydantic.condecimal() = Decimal("0")


class PositionOut(Position):
    pass


class Order(PydanticBaseModel):
    account_id: pydantic.types.UUID4
    symbol: pydantic.constr(max_length=20)
    side: enums.OrderSide
    type: enums.OrderType
    post_only: bool = False
    reduce_only: bool = False
    quantity: pydantic.condecimal(ge=Decimal('0.0')) = Decimal("0")
    price: pydantic.condecimal(ge=Decimal('0.0')) = Decimal("0")
    quote_quantity: pydantic.condecimal(ge=Decimal('0.0')) = Decimal("0")


class OrderOut(Order):
    id: pydantic.types.UUID4
    status: enums.OrderStatus
    filled_quantity: pydantic.condecimal(ge=Decimal('0.0')) = Decimal("0")
    filled_quote: pydantic.condecimal(ge=Decimal('0.0')) = Decimal("0")
    insert_time: datetime
    update_time: datetime
    leverage: int


class OrderIn(Order):
    @pydantic.root_validator()
    def order_validation(cls, values):
        for field in ['symbol', 'type', 'side']:
            if not field in values:
                return values
        contract = cls.get_contract(values['symbol'])
        if values['type'] == enums.OrderType.limit.value:
            for field in ['price', 'quantity']:
                if not field in values:
                    return values
            if values.get('quote_quantity'):
                raise ValueError(
                    "quote_quantity can't be sent for limit order"
                )
            elif values['quantity'] < contract.min_base_quantity:
                raise ValueError(
                    "quantity can't be lower than min_base_quantity of symbol")
            elif values['quantity'] * values['price'] < contract.min_quote_quantity:
                raise ValueError(
                    "order value can't be lower than min_quote_quantity of symbol")
            elif -values['quantity'].as_tuple().exponent > contract.quote_precision:
                raise ValueError(
                    "quantity decimal precision can't be more than base_precision of symbol")
            elif -values['price'].as_tuple().exponent > contract.base_precision:
                raise ValueError(
                    "price decimal precision can't be more than quote_precision of symbol")
        elif values['type'] == enums.OrderType.market.value:
            if values.get('post_only', False):
                raise ValueError(
                    "market order can't be post_only"
                )
            if values.get('price'):
                raise ValueError(
                    "price can't be sent for market order"
                )
            if values['side'] == enums.OrderSide.long.value:
                if values.get('quantity'):
                    raise ValueError(
                        "quantity can't be sent for market buy order"
                    )
                elif not values.get('quote_quantity'):
                    raise ValueError(
                        "quote_quantity must be sent for market buy order"
                    )
                elif -values['quote_quantity'].as_tuple().exponent > contract.base_precision:
                    raise ValueError(
                        "quote_quantity decimal precision can't be more than quote_precision of symbol")
                elif values['quote_quantity'] < contract.min_quote_quantity:
                    raise ValueError(
                        "order value can't be lower than min_quote_quantity of symbol")
            elif values['side'] == enums.OrderSide.short.value:
                if values.get('quote_quantity'):
                    raise ValueError(
                        "quote_quantity can't be sent for market sell order"
                    )
                elif not values.get('quantity'):
                    raise ValueError(
                        "quantity must be sent for market sell order"
                    )
                elif -values['quantity'].as_tuple().exponent > contract.quote_precision:
                    raise ValueError(
                        "quantity decimal precision can't be more than base_precision of symbol")
        values['base'] = contract.base_asset
        values['quote'] = contract.quote_asset
        db = next(database.get_db())
        try:
            account = db.query(models.Account).filter(
                models.Account.id == values['account_id']).one()
        except Exception as e:
            raise ValueError("Invalid accountId")
        values['leverage'] = account.leverage
        return values

    @classmethod
    def get_contract(cls, symbol):
        db = next(database.get_db())
        db_contract = db.query(models.Contract).filter(
            models.Contract.symbol == symbol
        ).first()

        if not db_contract:
            raise ValueError("symbol does not exsit")
        return ContractOut.from_orm(db_contract)

    def is_account_valid(self, wallet_address):
        db = next(database.get_db())
        try:
            db_wallet = db.query(models.Wallet).filter(
                models.Wallet.address == wallet_address,
            ).one()
            db_account = db.query(models.Account).filter(
                models.Account.id == self.account_id,
                models.Account.wallet_id == db_wallet.id
            ).one()
            return True
        except Exception as e:
            return False


class OrderBookOut(PydanticBaseModel):
    side: enums.OrderSide
    quantity: pydantic.condecimal(ge=Decimal('0.0')) = Decimal("0")
    price: pydantic.condecimal(ge=Decimal('0.0')) = Decimal("0")


class OrderCancel(PydanticBaseModel):
    id: pydantic.types.UUID4
    symbol: str

    class Config:
        orm_mode = True
        use_enum_values = True

    @classmethod
    def cancel_orders(cls, orders):
        canceled = []
        for order in orders:
            order = cls.from_orm(order)
            order.cancel_order()
            canceled.append(order)
        return canceled

    def cancel_order(self):
        kafka_client.publish(
            info=self,
            event_type=enums.EventType.cancel_order.value,
        )


class SubTrade(PydanticBaseModel):
    id: pydantic.types.UUID4
    order_id: pydantic.types.UUID4
    account_id: pydantic.types.UUID4
    symbol: pydantic.constr(max_length=20)
    price: pydantic.condecimal(ge=Decimal('0.0'))
    quantity: pydantic.condecimal(ge=Decimal('0.0'))
    quote_quantity: pydantic.condecimal(ge=Decimal('0.0'))
    commission: float
    commission_asset: str
    side: enums.OrderSide
    is_maker: bool
    insert_time: datetime

    # class Config:
    #     orm_mode = True
    #     use_enum_values = True


class SubTradeOut(SubTrade):
    pass


class PublicTrade(PydanticBaseModel):
    id: pydantic.types.UUID4
    # maker_order_id: pydantic.types.UUID4
    # taker_order_id: pydantic.types.UUID4
    price: pydantic.condecimal(ge=Decimal('0.0'))
    quantity: pydantic.condecimal(ge=Decimal('0.0'))
    # quote_quantity: pydantic.condecimal(gt=Decimal('0.0'))
    symbol: str = None
