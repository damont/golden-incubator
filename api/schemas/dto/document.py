from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    session_id: str
    content: str
    version: int
    created_at: str
