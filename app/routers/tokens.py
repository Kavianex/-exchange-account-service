from fastapi import APIRouter
import time
import settings
from internal import schemas

router = APIRouter(
    prefix="/token",
    tags=["token"],
    responses={404: {"description": "Not found"}},
)


@router.get("/text2sign/{wallet_address}", response_model=schemas.SignOut)
async def get_text2sign(wallet_address: str):
    expire = int(time.time() * 1000) + settings.TOKEN_EXPIRE_TIME
    text2sign = f"{wallet_address.lower()}:{expire}"
    return {
        "wallet_address": wallet_address,
        "expire": expire,
        "text2sign": text2sign
    }
