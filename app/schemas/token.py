from pydantic import BaseModel
from typing import Optional # For TokenPayload sub

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel): # Corresponds to what's in security.py TokenPayload
    sub: Optional[str] = None
    # exp: Optional[datetime] = None # exp is handled in security.py, not typically part of this schema for request/response bodies
    # If this TokenPayload is for responses, it might differ.
    # The one in security.py is for internal representation after decoding.
    # This one here might be for different uses, or could be removed if security.TokenPayload is sufficient.
    # For now, keeping it as per the script.
