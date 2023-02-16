from fastapi import FastAPI
from orm.database import engine, Base
from routers import wallets, networks, balances, accounts, orders, trades, tokens, assets, contracts, brokers, positions
import uvicorn
import settings

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(networks.router)
app.include_router(wallets.router)
app.include_router(accounts.router)
app.include_router(balances.router)
app.include_router(orders.router)
app.include_router(trades.router)
app.include_router(tokens.router)
app.include_router(assets.router)
app.include_router(contracts.router)
app.include_router(brokers.router)
app.include_router(positions.router)


@app.get("/")
async def root():
    return {"message": "Account service id running."}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.SERVICE_PORT)
