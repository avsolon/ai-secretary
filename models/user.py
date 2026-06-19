from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    is_admin: bool = False
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
