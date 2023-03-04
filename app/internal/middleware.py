from fastapi import HTTPException, Header, Depends, Request
from internal import enums
# from main import app
import settings


def verify_admin(role: str = Header('')):
    verified = False
    if not role:
        verified = False
    elif role == enums.Roles.admin.value:
        verified = True
    if not verified:
        raise HTTPException(401)
    return role


def verify_admin_or_service(role: str = Header(''), token: str = Header('')):
    verified = False
    if not role:
        verified = False
    elif role == enums.Roles.admin.value:
        verified = True
    elif role == enums.Roles.service.value:
        if token == settings.SECRET_TOKEN:
            verified = True
    if not verified:
        raise HTTPException(401)
    return role
