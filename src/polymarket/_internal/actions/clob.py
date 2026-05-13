from decimal import Decimal

from polymarket._internal.validation import require_nonempty
from polymarket.models.base import BaseModel


class _MidpointResponse(BaseModel):
    mid: Decimal


def build_midpoint_request(*, token_id: str) -> tuple[str, dict[str, str]]:
    require_nonempty("token_id", token_id)
    return "/midpoint", {"token_id": token_id}


def parse_midpoint(data: object) -> Decimal:
    return _MidpointResponse.parse_response(data).mid


__all__ = ["build_midpoint_request", "parse_midpoint"]
