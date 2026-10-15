"""Pydantic schemas for the chat API."""

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)


class SourceRef(BaseModel):
    dataset_id: str | None = None
    source: str | None = None
    treatment: str | None = None
    license: str | None = None


class ChatResponse(BaseModel):
    reply: str
    sources: list[SourceRef] = Field(default_factory=list)
    model: str
    provider: str
    fallback: bool
    guardrail_flags: list[str] = Field(default_factory=list)
    disclaimer: str
