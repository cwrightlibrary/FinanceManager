import json

from pathlib import Path
from pydantic import BaseModel, Field
from typing import Any


class GetProfile(BaseModel):
    profile_path: Path = Path(".user_profile.json")

    name: str = "Guest"
    data: dict = Field(default_factory=dict)

    def model_post_init(self, context: Any) -> None:
        if self.profile_path.exists():
            with open(self.profile_path, "r", encoding="utf-8") as file:
                self.data = json.load(file)
                self.name = self.data["name"]
