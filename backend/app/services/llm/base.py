from abc import ABC, abstractmethod
from typing import TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    @abstractmethod
    def generate_structured(self, system_prompt: str, user_prompt: str, response_model: type[T]) -> T:
        raise NotImplementedError
