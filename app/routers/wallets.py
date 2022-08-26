import uuid
from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from orm import database, models
from internal import schemas, middleware, enums

router = APIRouter(
    prefix="/wallet",
    tags=["wallet"],
    responses={404: {"description": "Not found"}},
)


@router.get("/byId/{wallet_id}", response_model=schemas.WalletOut)
async def get_by_id(wallet_id: uuid.UUID, db: Session = Depends(database.get_db)):
    db_wallet = db.query(models.Wallet).filter(
        models.Wallet.id == wallet_id).first()
    if not db_wallet:
        raise HTTPException(404)
    return db_wallet


@router.get("/{standard}", response_model=list[schemas.WalletOut])
async def get_all_by_standard(standard: str, db: Session = Depends(database.get_db)):
    return db.query(models.Wallet).filter(
        models.Wallet.standard == standard,
    ).all()


@router.get("/{standard}/{address}", response_model=schemas.WalletOut)
async def get(standard: str, address: str, db: Session = Depends(database.get_db)):
    db_wallet = db.query(models.Wallet).filter(
        models.Wallet.standard == standard,
        models.Wallet.address == address,
    ).first()
    if not db_wallet:
        raise HTTPException(404)
    return db_wallet


@router.post("/", response_model=schemas.WalletOut)
async def create(wallet_in: schemas.WalletIn, wallet: str = Header(), db: Session = Depends(database.get_db)):
    if not wallet_in.is_valid(wallet):
        raise HTTPException(400, 'this address and standard already exist.')
    wallet_in = wallet_in.dict()
    wallet_in['address'] = wallet
    if "referred_code" in wallet_in:
        referred_code = wallet_in.pop('referred_code')
        referred_wallet = db.query(models.Wallet).filter(
            models.Wallet.referral_code == referred_code).first()
        if referred_wallet:
            wallet_in['referred_wallet'] = referred_wallet.address
    wallet_in['referral_code'] = models.Wallet.generate_referral_code()
    db_wallet = models.Wallet(**wallet_in)
    db.add(db_wallet)
    db.commit()
    db.refresh(db_wallet)
    db_account = models.Account(
        wallet_id=db_wallet.id,
        name=enums.AccountType.main.value.lower(),
        type=enums.AccountType.main.value
    )
    db.add(db_account)
    db.commit()
    return db_wallet
