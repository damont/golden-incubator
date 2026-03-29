from pydantic import BaseModel


class SessionCreate(BaseModel):
    name: str


class SessionResponse(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str
