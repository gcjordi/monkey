from flask_security import Security
from itsdangerous import BadSignature, Serializer, SignatureExpired
from pydantic import PrivateAttr

from common.base_models import InfectionMonkeyBaseModel

from .types import Token


class TokenValidationError(Exception):
    """Raise when an invalid token is encountered"""


class ParsedToken(InfectionMonkeyBaseModel):
    raw_token: Token
    expiration_time: int
    user_uniquifier: str
    _token_serializer: Serializer = PrivateAttr()

    def __init__(self, token_serializer: Serializer, *, raw_token: Token, **data):
        self._token_serializer = token_serializer

        user_uniquifier = self._token_serializer.loads(raw_token)
        super().__init__(raw_token=raw_token, user_uniquifier=user_uniquifier, **data)

    def is_expired(self) -> bool:
        try:
            self._token_serializer.loads(self.raw_token, max_age=self.expiration_time)
            return False
        except SignatureExpired:
            return True


class TokenParser:
    def __init__(self, security: Security, token_expiration: int):
        self._token_serializer = security.remember_token_serializer
        self._token_expiration = token_expiration  # in seconds

    def parse(self, token: Token) -> ParsedToken:
        """
        Parses a token and returns a data structure with its components

        :param token: The token to parse
        :return: The parsed token
        :raises TokenValidationError: If the token could not be parsed
        """
        try:
            return ParsedToken(
                token_serializer=self._token_serializer,
                raw_token=token,
                expiration_time=self._token_expiration,
            )
        except BadSignature:
            raise TokenValidationError("Invalid token signature")
