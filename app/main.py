from fastapi import FastAPI, Request, Header, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from fastapi.openapi.utils import get_openapi
from orm import database, models
import json
from routers import wallets, networks, balances, accounts, orders, trades, tokens, assets, contracts, brokers, positions
import uvicorn
import settings
database.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Kavianex | API", version="0.1.0", docs_url=None)
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


def my_schema():
    openapi_schema = get_openapi(
        title="The Kavianex API Documents",
        version="1.0",
        routes=app.routes,
    )
    openapi_schema["info"] = {
        "title": "The Kavianex API Documents",
        "version": "1.0",
        "description": "Learn about programming language history!",
        "termsOfService": "http://www.kavianex.com/terms/",
        "contact": {
            "name": "Get Help with this API",
            # "url": "https://.com/help",
            "email": "info@kavianex.com"
        },
        "license": {
            "name": "MIT",
            "url": "https://opensource.org/license/mit/"
        },
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = my_schema


@app.middleware('http')
async def verify_account_id(request: Request, call_next):
    verified = True
    if not request.method == 'GET':
        path = request.url.path
        if path[-1] == '/' and path not in ['/wallet/', '/network/']:
            db = database.SessionLocal()
            try:
                wallet_address = request.headers['wallet']
                account_id = request.headers['account-id']
                db_wallet = db.query(models.Wallet).filter(
                    models.Wallet.address == wallet_address,
                ).one()
                db.query(models.Account).filter(
                    models.Account.id == account_id,
                    models.Account.wallet_id == db_wallet.id
                ).one()
            except Exception as e:
                verified = False
            db.close()
    if verified:
        response = await call_next(request)
    else:
        response = Response(status_code=403, content='invalid account_id')
    return response


@app.get("/")
async def root():
    return {"message": "API service is running."}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.SERVICE_PORT)
