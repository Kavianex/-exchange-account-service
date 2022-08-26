from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from orm import database, models
from internal import schemas


router = APIRouter(
    prefix="/subAccount",
    tags=["subaccount"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{standard}/{address}", response_model=list[schemas.AccountOut])
async def get_all(standard: str, address: str, db: Session = Depends(database.get_db)):
    db_wallet = db.query(models.Wallet).filter(
        models.Wallet.standard == standard,
        models.Wallet.address == address
    ).first()
    if not db_wallet:
        raise HTTPException(404)
    return db.query(models.Account).filter(models.Account.wallet_id == db_wallet.id).all()
