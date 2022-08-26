import os


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
