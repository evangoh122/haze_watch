"""Pydantic schemas for the chat API."""

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    # Only user/assistant turns are accepted from callers; `system` is reserved
    # for the application policy prompt (prevents instruction smuggling).
    role: Literal["user", "assistant"]
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
