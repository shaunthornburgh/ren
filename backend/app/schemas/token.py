from pydantic import BaseModel


class Token(BaseModel):
    """OAuth2-style bearer token response."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Decoded JWT claims we rely on."""

    sub: str | None = None
    role: str | None = None
