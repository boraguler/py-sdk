from polymarket.errors import UserInputError


def require_nonempty(name: str, value: str) -> str:
    if not value:
        raise UserInputError(f"{name} is required")
    return value


__all__ = ["require_nonempty"]
