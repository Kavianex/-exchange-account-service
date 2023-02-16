import uuid
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from orm import database, models
from internal import schemas, middleware


router = APIRouter(
    prefix="/broker",
    tags=["broker"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=list[schemas.BrokerOut])
async def get_all(db: Session = Depends(database.get_db)):
    return db.query(models.Broker).all()


@router.get("/{broker_id}", response_model=schemas.BalanceOut)
async def get_all(broker_id: uuid.UUID, db: Session = Depends(database.get_db)):
    db_broker = db.query(models.Broker).filter(
        models.Broker.id == broker_id,
    ).first()
    if not db_broker:
        raise HTTPException(404)
    return db_broker


@router.post("/", response_model=schemas.BrokerOut, dependencies=[Depends(middleware.verify_admin)])
async def create(broker_in: schemas.BrokerIn, db: Session = Depends(database.get_db)):
    db_broker = models.Contract(**broker_in.dict())
    db.add(db_broker)
    db.commit()
    db.refresh(db_broker)
    return db_broker
