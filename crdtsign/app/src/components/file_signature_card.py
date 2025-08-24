import flet as ft
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class FileSignatureCard:
    file_name: str
    file_hash: str
    signature: str
    username: str
    user_id: str
    signed_on: datetime
    expiration_date: Optional[datetime]

