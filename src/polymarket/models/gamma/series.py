"""Series models."""

from __future__ import annotations

from polymarket.models.gamma.common import (
    CategoryReference,
    Chat,
    CollectionReference,
    SeriesReference,
)
from polymarket.models.gamma.event import Event
from polymarket.models.gamma.tag import Tag


class Series(SeriesReference):
    events: tuple[Event, ...] | None = None
    collections: tuple[CollectionReference, ...] | None = None
    categories: tuple[CategoryReference, ...] | None = None
    chats: tuple[Chat, ...] | None = None
    tags: tuple[Tag, ...] | None = None


__all__ = ["Series"]
