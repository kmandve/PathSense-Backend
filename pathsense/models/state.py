from dataclasses import dataclass, field
from typing import Any


@dataclass
class AppState:
    vision_model: Any = field(default=None)
    tokenizer: Any = field(default=None)
