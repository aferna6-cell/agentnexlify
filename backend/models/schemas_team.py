from datetime import datetime

from pydantic import BaseModel, field_validator


class TeamInviteRequest(BaseModel):
    email: str
    role: str = "member"
    name: str | None = None

    @field_validator("email")
    @classmethod
    def validate_invite_email(cls, v: str) -> str:
        import re
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", v):
            raise ValueError("Invalid email address")
        return v.lower().strip()

    @field_validator("role")
    @classmethod
    def validate_invite_role(cls, v: str) -> str:
        if v not in ("admin", "member", "viewer"):
            raise ValueError("role must be one of: admin, member, viewer")
        return v


class TeamMemberResponse(BaseModel):
    id: str
    email: str
    name: str | None = None
    role: str
    invite_accepted: bool
    last_login: datetime | None = None
    created_at: datetime


class AcceptInviteRequest(BaseModel):
    token: str
    name: str
    password: str
    email: str

    @field_validator("password")
    @classmethod
    def validate_accept_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class InviteValidationResponse(BaseModel):
    email: str
    business_name: str
    role: str
