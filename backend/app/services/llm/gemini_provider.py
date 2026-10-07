from typing import TypeVar

from pydantic import BaseModel
from google import genai
from google.genai import types, errors

from app.services.llm.base import LLMProvider


T = TypeVar("T", bound=BaseModel)


class GeminiProvider(LLMProvider):

    def __init__(self, api_key: str, models: list[str]):
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is required when LLM_PROVIDER=gemini"
            )

        if not models:
            raise ValueError(
                "At least one Gemini model must be configured"
            )

        self.client = genai.Client(api_key=api_key)
        self.models = models

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:

        last_error = None

        for model in self.models:

            try:
                print(f"[Gemini] Trying model: {model}")

                response = self.client.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        response_schema=response_model,
                    ),
                )

                if response.parsed is not None:

                    if isinstance(response.parsed, response_model):
                        print(f"[Gemini] Success with: {model}")
                        return response.parsed

                    print(f"[Gemini] Success with: {model}")

                    return response_model.model_validate(
                        response.parsed
                    )

                if response.text:

                    print(f"[Gemini] Success with: {model}")

                    return response_model.model_validate_json(
                        response.text
                    )

                raise RuntimeError(
                    f"Gemini model {model} returned an empty response"
                )

            except errors.ServerError as exc:

                last_error = exc

                print(
                    f"[Gemini] {model} unavailable "
                    f"({exc.code}). Trying next model..."
                )

                continue
            
            except errors.ClientError as exc:

                if exc.code == 429:

                    last_error = exc

                    print(
                        f"[Gemini] {model} rate limited. "
                        "Trying next model..."
                    )

                    continue

                raise

        raise RuntimeError(
            f"All configured Gemini models failed. "
            f"Last error: {last_error}"
        )