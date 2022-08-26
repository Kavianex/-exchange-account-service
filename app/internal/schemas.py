from audioop import add
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import requests
import pydantic
from orm import database, models
from . import enums
import settings


class Account(pydantic.BaseModel):
    wallet_id: pydantic.types.UUID4
    name: str
    type: enums.AccountType

    class Config:
        orm_mode = True
        use_enum_values = True


class AccountOut(Account):
    id: pydantic.types.UUID4


class AccountIn(Account):
    pass


class Balance(pydantic.BaseModel):
    asset: pydantic.types.constr(max_length=10)
    account_id: pydantic.types.UUID4

    class Config:
        orm_mode = True
        use_enum_values = True


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


class Wallet(pydantic.BaseModel):
    standard: pydantic.types.constr(min_length=3, max_length=10)

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
        print(address, self.standard)
        wallet = db.query(models.Wallet).filter(
            models.Wallet.standard == self.standard,
            models.Wallet.address == address,
        ).first()
        db.close()
        if wallet:
            return False
        return True

    @pydantic.validator('standard')
    def check_exist(cls, v):
        db = database.SessionLocal()
        network = db.query(models.Network).filter(
            models.Network.standard == v).first()
        db.close()
        if not network:
            raise ValueError('invalid standard for network.')
        return v


class Network(pydantic.BaseModel):
    name: pydantic.types.constr(min_length=5)
    standard: pydantic.types.constr(min_length=3)
    rpc_url: pydantic.HttpUrl
    chain_id: pydantic.types.conint(gt=1)
    chain_hex: pydantic.types.constr(min_length=3)
    symbol: pydantic.types.constr(min_length=2)
    block_explorer_url: pydantic.HttpUrl
    address: pydantic.types.constr(min_length=20, max_length=50)

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


class Crypto(pydantic.BaseModel):
    symbol: pydantic.types.constr(
        min_length=2, max_length=10, strip_whitespace=True)
    name: pydantic.types.constr(min_length=5, max_length=80)
    standard: pydantic.types.constr(min_length=5)
    kind: enums.CryptoKind = enums.CryptoKind.token.value
    contract: pydantic.types.constr(
        min_length=10, strip_whitespace=True, max_length=100) = None
    digits: pydantic.types.conint(gt=5)

    class Config:
        orm_mode = True
        use_enum_values = True


class CryptoOut(Crypto):
    pass


class CryptoIn(Crypto):
    @pydantic.validator('standard')
    def check_exist(cls, v):
        db = database.SessionLocal()
        network = db.query(models.Network).filter(
            models.Network.standard == v).first()
        db.close()
        if not network:
            raise ValueError('invalid standard for network.')
        return v


class Order(pydantic.BaseModel):
    account_id: pydantic.types.UUID4
    symbol: pydantic.constr(max_length=20)
    side: enums.OrderSide
    type: enums.OrderType
    quantity: pydantic.condecimal(ge=Decimal('0.0')) = Decimal("0")
    price: pydantic.condecimal(ge=Decimal('0.0')) = Decimal("0")
    quote_quantity: pydantic.condecimal(ge=Decimal('0.0')) = Decimal("0")

    class Config:
        orm_mode = True
        use_enum_values = True


class OrderOut(Order):
    id: pydantic.types.UUID4
    status: enums.OrderStatus
    filled_quantity: float = 0
    filled_quote: float = 0
    insert_time: datetime
    update_time: datetime


class OrderIn(Order):
    @pydantic.root_validator()
    def order_validation(cls, values):
        for field in ['symbol', 'type', 'side']:
            if not field in values:
                return values
        symbol_info = cls.get_symbol(values['symbol'])
        if values['type'] == enums.OrderType.limit.value:
            for field in ['price', 'quantity']:
                if not field in values:
                    return values
            if values.get('quote_quantity'):
                raise ValueError(
                    "quote_quantity can't be sent for limit order"
                )
            elif values['quantity'] < symbol_info['min_base_quantity']:
                raise ValueError(
                    "quantity can't be lower than min_base_quantity of symbol")
            elif values['quantity'] * values['price'] < symbol_info['min_quote_quantity']:
                raise ValueError(
                    "order value can't be lower than min_quote_quantity of symbol")
            elif -values['quantity'].as_tuple().exponent > symbol_info['quote_precision']:
                raise ValueError(
                    "quantity decimal precision can't be more than base_precision of symbol")
            elif -values['price'].as_tuple().exponent > symbol_info['base_precision']:
                raise ValueError(
                    "price decimal precision can't be more than quote_precision of symbol")
        elif values['type'] == enums.OrderType.market.value:
            if values.get('price'):
                raise ValueError(
                    "price can't be sent for market order"
                )
            if values['side'] == enums.OrderSide.buy.value:
                if values.get('quantity'):
                    raise ValueError(
                        "quantity can't be sent for market buy order"
                    )
                elif not values.get('quote_quantity'):
                    raise ValueError(
                        "quote_quantity must be sent for market buy order"
                    )
                elif -values['quote_quantity'].as_tuple().exponent > symbol_info['base_precision']:
                    raise ValueError(
                        "quote_quantity decimal precision can't be more than quote_precision of symbol")
                elif values['quote_quantity'] < symbol_info['min_quote_quantity']:
                    raise ValueError(
                        "order value can't be lower than min_quote_quantity of symbol")
            elif values['side'] == enums.OrderSide.sell.value:
                if values.get('quote_quantity'):
                    raise ValueError(
                        "quote_quantity can't be sent for market sell order"
                    )
                elif not values.get('quantity'):
                    raise ValueError(
                        "quantity must be sent for market sell order"
                    )
                elif -values['quantity'].as_tuple().exponent > symbol_info['quote_precision']:
                    raise ValueError(
                        "quantity decimal precision can't be more than base_precision of symbol")
        values['base'] = symbol_info['base_asset']
        values['quote'] = symbol_info['quote_asset']
        return values

    @classmethod
    def get_symbol(cls, symbol):
        url = f"{settings.SERVICE_HOSTS['market']}/symbol/{symbol}"
        response = requests.get(url=url)
        if not response.status_code == 200:
            raise ValueError("symbol does not exsit")
        return response.json()

    # @pydantic.validator('price')
    # def symbol_exis(cls, v):
    #     print('price')
    #     return v


class SubTrade(pydantic.BaseModel):
    id: pydantic.types.UUID4
    order_id: pydantic.types.UUID4
    account_id: pydantic.types.UUID4
    symbol: pydantic.constr(max_length=20)
    price: pydantic.condecimal(gt=Decimal('0.0'))
    quantity: pydantic.condecimal(gt=Decimal('0.0'))
    quote_quantity: pydantic.condecimal(gt=Decimal('0.0'))
    commission: float
    commission_asset: str
    side: enums.OrderSide
    is_maker: bool
    insert_time: datetime

    class Config:
        orm_mode = True
        use_enum_values = True


class SubTradeOut(SubTrade):
    pass


class Trade(pydantic.BaseModel):
    maker_order_id: pydantic.types.UUID4
    taker_order_id: pydantic.types.UUID4
    price: pydantic.condecimal(gt=Decimal('0.0'))
    quantity: pydantic.condecimal(gt=Decimal('0.0'))
    quote_quantity: pydantic.condecimal(gt=Decimal('0.0'))

    class Config:
        orm_mode = True
        use_enum_values = True
