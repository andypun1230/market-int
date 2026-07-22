from typing import Any, Literal

from pydantic import BaseModel, Field


CopilotSourceState = Literal[
    "live",
    "delayed",
    "cached",
    "stale",
    "test",
    "partial",
    "mock",
    "mixed",
    "unavailable",
]


class CopilotMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class CopilotChatRequest(BaseModel):
    request_id: str | None = Field(default=None, alias="requestId")
    thread_id: str | None = Field(default=None, alias="threadId")
    message: str
    context: dict[str, Any] = Field(default_factory=dict)
    screen_context: dict[str, Any] = Field(default_factory=dict, alias="screenContext")
    session_context: dict[str, Any] | None = Field(default=None, alias="sessionContext")
    history: list[CopilotMessage] = Field(default_factory=list)
    response_depth: Literal["compact", "standard", "detailed"] = Field(default="compact", alias="responseDepth")

    class Config:
        populate_by_name = True

    @property
    def effective_context(self) -> dict[str, Any]:
        # `context` is the existing transport field; `screenContext` is the
        # Stage 7 typed alias.  Screen/member hints are merged, while the
        # orchestrator still ignores any client-supplied market values.
        return {**self.context, **self.screen_context}


class CopilotGrounding(BaseModel):
    context_used: list[str] = Field(default_factory=list, alias="contextUsed")
    source_state: CopilotSourceState = Field(default="unavailable", alias="sourceState")
    generated_at: str = Field(alias="generatedAt")

    class Config:
        populate_by_name = True


class CopilotAnswerSections(BaseModel):
    direct_answer: str = Field(alias="directAnswer")
    why: list[str] = Field(default_factory=list)
    main_caution: str | None = Field(default=None, alias="mainCaution")
    what_would_change: list[str] = Field(default_factory=list, alias="whatWouldChange")

    class Config:
        populate_by_name = True


class CopilotAnswerConfidence(BaseModel):
    level: Literal["high", "moderate", "limited"]
    reasons: list[str] = Field(default_factory=list)


class CopilotChatResponse(BaseModel):
    thread_id: str = Field(alias="threadId")
    answer: str
    answer_sections: CopilotAnswerSections | None = Field(default=None, alias="answerSections")
    grounding: CopilotGrounding
    suggested_follow_ups: list[str] = Field(default_factory=list, alias="suggestedFollowUps")
    confidence: int
    answer_confidence: CopilotAnswerConfidence | None = Field(default=None, alias="answerConfidence")
    generated_by: str = Field(alias="generatedBy")
    disclaimer: str

    class Config:
        populate_by_name = True
