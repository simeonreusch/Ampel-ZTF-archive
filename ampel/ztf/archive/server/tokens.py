import sqlalchemy
from ampel.ztf.archive.ArchiveDB import ArchiveDB, select
from typing import List
import jwt

from pydantic import BaseModel, ValidationError
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials

from .settings import settings
from .db import get_archive

bearer = HTTPBearer()


class User(BaseModel):

    name: str
    orgs: List[str]
    teams: List[str]


class TokenRequest(BaseModel):
    token: str


async def get_user(auth: HTTPAuthorizationCredentials = Depends(bearer)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            auth.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        try:
            token_data = User(**payload)
            return token_data
        except ValidationError:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

def find_access_token(db: ArchiveDB, token: str) -> bool:
    Token = db._meta.tables["access_token"]
    with db._engine.connect() as conn:
        try:
            cursor = conn.execute(
                select([Token.c.id]).where(Token.c.id == token).limit(1)
            )
        except sqlalchemy.exc.DataError:
            # e.g. invalid input syntax for type uuid
            return False
        return bool(cursor.fetchone())

async def verify_access_token(
    auth: HTTPAuthorizationCredentials = Depends(bearer), db=Depends(get_archive)
) -> bool:
    if not find_access_token(db, auth.credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True


router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_token(user: User = Depends(get_user), db: ArchiveDB = Depends(get_archive)):
    Token = db._meta.tables["access_token"]
    with db._engine.connect() as conn:
        cursor = conn.execute(Token.insert({"owner": user.name}).returning(Token.c.id))
        return cursor.fetchone()["id"]


@router.get("/")
def list_tokens(user: User = Depends(get_user), db: ArchiveDB = Depends(get_archive)):
    Token = db._meta.tables["access_token"]
    with db._engine.connect() as conn:
        cursor = conn.execute(Token.select().where(Token.c.owner == user.name))
        return cursor.fetchall()


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_token(
    token: TokenRequest,
    user: User = Depends(get_user),
    db: ArchiveDB = Depends(get_archive),
):
    Token = db._meta.tables["access_token"]
    with db._engine.connect() as conn:
        conn.execute(
            Token.delete().where(
                Token.c.id == token.token and Token.c.owner == user.name
            )
        )
