"""Request limits and model-output validation at the trust boundaries."""

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="before")
    @classmethod
    def valid_unicode(cls, value):
        if isinstance(value, str) and any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise ValueError("Text contains an unpaired Unicode surrogate")
        return value


class DocumentInput(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    url: str = Field(default="", max_length=2048)
    text: str = Field(min_length=20, max_length=80000)

    @field_validator("url")
    @classmethod
    def safe_url(cls, value: str) -> str:
        if value:
            url = urlparse(value)
            if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
                raise ValueError("Source URL must be http(s), without credentials")
        return value


class Turn(StrictModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatInput(StrictModel):
    document_id: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=2, max_length=1000)
    persona: Literal["whale", "mochi", "senpai"] = "whale"
    history: list[Turn] = Field(default_factory=list, max_length=8)


class StudyInput(StrictModel):
    document_id: str = Field(min_length=1, max_length=64)
    persona: Literal["whale", "mochi", "senpai"] = "whale"


class Card(StrictModel):
    title: str = Field(min_length=1, max_length=100)
    body: str = Field(min_length=1, max_length=1200)
    source_id: str = Field(pattern=r"^S\d+$")


class Quiz(StrictModel):
    question: str = Field(min_length=1, max_length=500)
    options: list[str] = Field(min_length=4, max_length=4)
    answer: int = Field(ge=0, le=3)
    explanation: str = Field(min_length=1, max_length=1000)
    source_id: str = Field(pattern=r"^S\d+$")

    @model_validator(mode="after")
    def unique_options(self):
        if len(set(self.options)) != len(self.options) or any(not x.strip() or len(x) > 400 for x in self.options):
            raise ValueError("Quiz choices must be distinct non-empty strings")
        return self


class StudyOutput(StrictModel):
    cards: list[Card] = Field(min_length=1, max_length=3)
    quiz: list[Quiz] = Field(min_length=1, max_length=3)

    def validate_sources(self, valid_ids: set[str]):
        if any(item.source_id not in valid_ids for item in [*self.cards, *self.quiz]):
            raise ValueError("Model returned a citation absent from the supplied sources")
        return self
