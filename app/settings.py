import os
from decimal import Decimal

_APPLICATION_MODE = os.getenv("APPLICATION_MODE", "PRODUCTION")
TESTNET_AAPLICATION = _APPLICATION_MODE == "TESTNET"

DBNAME = os.getenv("POSTGRES_DB", "dbname")
DBUSER = os.getenv("POSTGRES_USER", "dbuser")
DBPASS = os.getenv("POSTGRES_PASSWORD", "dbpass")
DBHOST = os.getenv("POSTGRES_HOST", "localhost")
DBPORT = os.getenv("POSTGRES_PORT", "5432")

RABBITMQ_CRED = os.getenv("RABBITMQ_CRED", "guest")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "127.0.0.1")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8000))
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "SECRET_TOKEN")
SERVICE_HOSTS = {
    "market": os.getenv('MARKET_HOST', 'http://127.0.0.1:8001'),
    "account": os.getenv('ACCOUNT_HOST', 'http://127.0.0.1:8003'),
}
TOKEN_EXPIRE_TIME = int(os.getenv("TOKEN_EXPIRE_TIME", 4 * 3600 * 1000))
API_TOKEN_EXPIRE_TIME = int(
    os.getenv("API_TOKEN_EXPIRE_TIME", 365 * 24 * 3600 * 1000))
ETHERSCAN_APIKEY = os.getenv(
    "ETHERSCAN_APIKEY", "")
FEES = {
    "TAKER": Decimal("0.003"),
    "MAKER": Decimal("-0.0015"),
    "EXCHANGE": Decimal("0.0005"),
    "BROKER": Decimal("0.0005"),
    "REFERRAL": Decimal("0.0005"),
}
assert abs(FEES["TAKER"]) > abs(
    FEES["MAKER"]) and FEES["MAKER"] < Decimal('0.0')
assert FEES["EXCHANGE"] > Decimal('0.0') and FEES["BROKER"] > Decimal(
    '0.0') and FEES["REFERRAL"] > Decimal('0.0')
assert FEES["TAKER"] - abs(FEES["MAKER"]) == FEES["EXCHANGE"] + \
    FEES["BROKER"] + FEES["REFERRAL"]

_KAFKA_SERVERS = [
    {
        "host": os.getenv('KAFKA_HOST1', '0.0.0.0'),
        "port": os.getenv('KAFKA_HOST1PORT', '9092'),
    },
    {
        "host": os.getenv('KAFKA_HOST2', ''),
        "port": os.getenv('KAFKA_HOST2PORT', '9092'),
    },
    {
        "host": os.getenv('KAFKA_HOST3', ''),
        "port": os.getenv('KAFKA_HOST3PORT', '9092'),
    },
]
KAFKA_BOOTSTRAP_SERVERS = ','.join([
    f"{bootstrap_server['host']}:{bootstrap_server['port']}" for bootstrap_server in _KAFKA_SERVERS if bootstrap_server['host']]
)
