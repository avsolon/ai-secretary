from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class BookingSession:
    user_id: int = 0
    state: str = "idle"
    service: Optional[str] = None
    services: List[str] = field(default_factory=list)
    date: Optional[str] = None
    time: Optional[str] = None
    start_iso: Optional[str] = None
    end_iso: Optional[str] = None
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    comment: Optional[str] = None
    temp_data: Dict[str, Any] = field(default_factory=dict)

    def reset(self):
        self.state = "idle"
        self.service = None
        self.services = []
        self.date = None
        self.time = None
        self.start_iso = None
        self.end_iso = None
        self.client_name = None
        self.client_phone = None
        self.comment = None
        self.temp_data = {}
