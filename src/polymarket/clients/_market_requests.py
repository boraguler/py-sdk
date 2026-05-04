"""Market lookup helpers."""

from urllib.parse import quote, urlparse

from polymarket.environments import Environment
from polymarket.errors import UserInputError


def build_market_request_url(
    environment: Environment,
    *,
    id: str | None,
    slug: str | None,
    url: str | None,
) -> str:
    lookup_type, value = _resolve_market_lookup(id=id, slug=slug, url=url)

    if lookup_type == "id":
        return f"{environment.gamma_url}/markets/{quote(value, safe='')}"

    if lookup_type == "url":
        value = _parse_market_slug_url(value)

    return f"{environment.gamma_url}/markets/slug/{quote(value, safe='')}"


def _resolve_market_lookup(
    *,
    id: str | None,
    slug: str | None,
    url: str | None,
) -> tuple[str, str]:
    provided = [("id", id), ("slug", slug), ("url", url)]
    selected = [(lookup_type, value) for lookup_type, value in provided if value is not None]

    if len(selected) != 1:
        raise UserInputError("Provide exactly one of id, slug, or url.")

    lookup_type, value = selected[0]
    if value == "":
        raise UserInputError(f"Market {lookup_type} cannot be empty.")

    return lookup_type, value


def _parse_market_slug_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if parsed.scheme != "https" or parsed.netloc not in {"polymarket.com", "www.polymarket.com"}:
        raise UserInputError("Expected a valid Polymarket URL.")

    segments = [segment for segment in parsed.path.split("/") if segment]
    if len(segments) != 2 or segments[0] != "market":
        raise UserInputError("Expected a Polymarket market URL.")

    return segments[1]
