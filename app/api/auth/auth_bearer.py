from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel

from .auth_handler import decode_jwt


class JWTHeader(BaseModel):
    user_id: int
    expires: float
    lawyer: bool = False


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True, lawyer: bool = False):
        super(JWTBearer, self).__init__(auto_error=auto_error)
        self.lawyer = lawyer

    async def __call__(self, request: Request) -> JWTHeader:
        authorization: str = request.headers.get("Authorization")

        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header missing")

        scheme, _, token = authorization.partition(" ")

        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")

        if not token:
            raise HTTPException(status_code=401, detail="Token not found")

        decoded = self.verify_jwt(token)
        if not decoded:
            raise HTTPException(
                status_code=401, detail="Invalid token or expired token."
            )

        header = JWTHeader(**decoded)

        if self.lawyer and not header.lawyer:
            raise HTTPException(status_code=401, detail="Lawyer privileges required")

        return header

    @staticmethod
    def verify_jwt(jwt_token: str):
        payload = decode_jwt(jwt_token)
        return payload if payload else None
