from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AttendanceCreateDTO(BaseModel):
    competitions_id: str
    users_id: Optional[str] = None

class AttendanceReadDTO(BaseModel):
    id: str
    users_id: str
    competitions_id: str
    timestamp: datetime

    class Config:
        from_attributes = True