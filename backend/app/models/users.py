from datetime import datetime
from typing import Optional

from passlib.context import CryptContext
from pydantic import Field, EmailStr, BaseModel
from pymongo import MongoClient

from app.models.mongomodel import MongoModel

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserBase(MongoModel):
    email: EmailStr


class UserIn(UserBase):
    first_name: str
    last_name: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserDB(UserBase):
    first_name: str
    last_name: str
    hashed_password: str = Field()
    keycloak_id: Optional[str] = None

    def verify_password(self, password):
        return pwd_context.verify(password, self.hashed_password)


class UserOut(UserBase):
    first_name: str
    last_name: str


class UserAPIKey(MongoModel):
    """API keys can have a reference name (e.g. 'Uploader script')"""

    key: str
    name: str
    user: EmailStr
    created: datetime = Field(default_factory=datetime.utcnow)
    expires: Optional[datetime] = None


class UserAPIKeyOut(MongoModel):
    # don't show the raw key
    name: str
    user: EmailStr
    created: datetime = Field(default_factory=datetime.utcnow)
    expires: Optional[datetime] = None


async def get_user_out(user_id: str, db: MongoClient) -> UserOut:
    """Retrieve user from Mongo based on email address."""
    user_out = await db["users"].find_one({"email": user_id})
    return UserOut.from_mongo(user_out)


def get_anonymous_user() -> UserOut:
    first_name = "Anonymous"
    last_name = "User"
    email = "anonymoususer@anonymoususer.com"
    anonymous_dict = {"first_name": first_name, "last_name": last_name, "email": email}
    anonymous_user_out = UserOut.from_mongo(anonymous_dict)
    return anonymous_user_out
