from typing import Any, Literal

from pydantic import BaseModel, Field


CopilotSourceState = Literal[
    "live",
    "delayed",
    "cached",
    "stale",
    "mock",
    "mixed",
    "unavailable",
]


class CopilotMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class CopilotChatRequest(BaseModel):
    thread_id: str | None = Field(default=None, alias="threadId")
    message: str
    context: dict[str, Any] = Field(default_factory=dict)
    history: list[CopilotMessage] = Field(default_factory=list)
    response_depth: Literal["compact", "standard", "detailed"] = Field(default="compact", alias="responseDepth")

    class Config:
        populate_by_name = True


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
