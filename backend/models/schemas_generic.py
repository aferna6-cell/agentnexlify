from pydantic import BaseModel, EmailStr


class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    message: str


class ContactResponse(BaseModel):
    success: bool
    message: str


class ChatMessageRequest(BaseModel):
    client_api_key: str
    session_id: str
    message: str


class ChatMessageResponse(BaseModel):
    reply: str
    conversation_id: str


class FaqEntryResponse(BaseModel):
    id: str
    question: str
    answer: str
    category: str | None = None
    is_active: bool = True


class FaqCreateRequest(BaseModel):
    question: str
    answer: str
    category: str | None = None
