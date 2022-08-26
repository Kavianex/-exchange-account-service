from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from orm import database, models
from internal import schemas, middleware

router = APIRouter(
    prefix="/network",
    tags=["network"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=list[schemas.NetworkOut])
async def get_all(db: Session = Depends(database.get_db)):
    return db.query(models.Network).all()


@router.get("/{standard}", response_model=schemas.NetworkOut)
async def get(standard: str, db: Session = Depends(database.get_db)):
    db_network = db.query(models.Network).filter(
        models.Network.standard == standard
    ).first()
    if not db_network:
        raise HTTPException(status_code=404, detail="Not found")
    return db_network


@router.post("/", response_model=schemas.NetworkOut, dependencies=[Depends(middleware.verify_admin)])
async def create(network_in: schemas.NetworkIn, db: Session = Depends(database.get_db)):
    db_network = models.Network(**network_in.dict())
    db.add(db_network)
    db.commit()
    db.refresh(db_network)
    return db_network
