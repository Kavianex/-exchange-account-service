from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from orm import database, models
from internal import schemas, middleware

router = APIRouter(
    prefix="/crypto",
    tags=["crypto"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=list[schemas.CryptoOut])
async def get_all(db: Session = Depends(database.get_db)):
    return db.query(models.Crypto).all()


@router.get("/{standard}", response_model=list[schemas.CryptoOut])
async def get_all_standard(standard: str, db: Session = Depends(database.get_db)):
    return db.query(models.Crypto).filter(
        models.Crypto.standard == standard,
    ).all()


@router.get("/{standard}/{symbol}", response_model=schemas.CryptoOut)
async def get(standard: str, symbol: str, db: Session = Depends(database.get_db)):
    db_crypto = db.query(models.Crypto).filter(
        models.Crypto.symbol == symbol,
        models.Crypto.standard == standard,
    ).first()
    if not db_crypto:
        raise HTTPException(status_code=404, detail="Not found")
    return db_crypto


@router.post("/", response_model=schemas.CryptoOut, dependencies=[Depends(middleware.verify_admin)])
async def create(crypto_in: schemas.CryptoIn, db: Session = Depends(database.get_db)):
    db_crypto = models.Crypto(**crypto_in.dict())
    db.add(db_crypto)
    db.commit()
    db.refresh(db_crypto)
    return db_crypto
