import os
from decimal import Decimal

DBNAME = os.getenv("POSTGRES_DB", "dbname")
DBUSER = os.getenv("POSTGRES_USER", "dbuser")
DBPASS = os.getenv("POSTGRES_PASSWORD", "dbpass")
DBHOST = os.getenv("POSTGRES_HOST", "localhost")
DBPORT = os.getenv("POSTGRES_PORT", "5432")

SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8000))
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "SECRET_TOKEN")
SERVICE_HOSTS = {
    "market": os.getenv('MARKET_HOST', 'http://127.0.0.1:8001'),
    "account": os.getenv('ACCOUNT_HOST', 'http://127.0.0.1:8003'),
}
FEES = {
    "TAKER": Decimal("0.003"),
    "MAKER": Decimal("-0.0015"),
}
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
