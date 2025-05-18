import time

import jwt
from config import settings


def sign_jwt(user_id: int, lawyer: bool = False) -> str:
    payload = {"user_id": user_id, "expires": time.time() + 86400, "lawyer": lawyer}
    token = jwt.encode(
        payload,
        settings.jwt_settings.secret_key,
        algorithm=settings.jwt_settings.algorithm,
    )

    return token


def decode_jwt(token: str):
    """
    :param token: jwt token
    :return:
    :rtype: None | dict
    """
    try:
        decoded_token = jwt.decode(
            token,
            settings.jwt_settings.secret_key,
            algorithms=[settings.jwt_settings.algorithm],
        )
    except Exception:
        return None
    return decoded_token if decoded_token["expires"] >= time.time() else None
