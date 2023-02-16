from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from orm import database, models
from internal import schemas, enums, middleware

router = APIRouter(
    prefix="/contract",
    tags=["contract"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=list[schemas.ContractOut])
async def get_all(db: Session = Depends(database.get_db)):
    return db.query(models.Contract).all()


@router.get("/{symbol}", response_model=schemas.ContractOut)
async def get(symbol: str, db: Session = Depends(database.get_db)):
    db_contract = db.query(models.Contract).filter(
        models.Contract.symbol == symbol
    ).first()
    if not db_contract:
        raise HTTPException(status_code=404, detail="Not found")
    return db_contract


@router.post("/", response_model=schemas.ContractOut, dependencies=[Depends(middleware.verify_admin)])
async def create(contract_in: schemas.ContractIn, db: Session = Depends(database.get_db)):
    contract = contract_in.dict()
    contract['symbol'] = f"{contract_in.base_asset}{contract_in.quote_asset}".upper(
    )
    contract['status'] = enums.ContractStatus.trading.value
    db_contract = models.Contract(**contract)
    db.add(db_contract)
    db.commit()
    db.refresh(db_contract)
    return db_contract
