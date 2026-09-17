from pydantic import BaseModel
from typing import Optional, List


# ----------create user------------
class Register(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    confirm_password: str


class GetUser(BaseModel):
    email: str
    password: str


class UpdateUser(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    confirm_password: Optional[str] = None


# ----------token data------------
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str

