from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ValidationError

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
# Ensure SECRET_KEY is loaded as a string
SECRET_KEY = str(settings.SECRET_KEY)


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[datetime] = None # JWT standard 'exp' claim


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def decode_token(token: str) -> Optional[TokenPayload]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Validate standard 'exp' claim, 'sub' is optional by our model
        # Store 'exp' as datetime if present
        exp_timestamp = payload.get("exp")
        exp_datetime = datetime.fromtimestamp(exp_timestamp, timezone.utc) if exp_timestamp else None

        token_data = TokenPayload(sub=payload.get("sub"), exp=exp_datetime)

        # Explicitly check expiration if not handled by jwt.decode (it usually is)
        if token_data.exp and token_data.exp < datetime.now(timezone.utc):
            return None # Token is expired

        return token_data
    except JWTError: # Catches all JWT errors, e.g., expired signature, invalid signature
        return None
    except ValidationError: # Pydantic validation error for TokenPayload
        return None
