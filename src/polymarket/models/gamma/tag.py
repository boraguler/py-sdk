"""Tag models."""

from __future__ import annotations

from pydantic import Field

from polymarket.models.base import BaseModel
from polymarket.models.gamma.common import Chat, TagReference, TemplateReference


class Tag(TagReference):
    chats: tuple[Chat, ...] | None = None
    templates: tuple[TemplateReference, ...] | None = None


class RelatedTag(BaseModel):
    id: str
    tag_id: int | None = Field(default=None, validation_alias="tagID")
    related_tag_id: int | None = Field(default=None, validation_alias="relatedTagID")
    rank: int | None = None


__all__ = ["RelatedTag", "Tag"]
