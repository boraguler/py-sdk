from polymarket.errors import UserInputError


def require_nonempty(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise UserInputError(f"{name} must be a string, got {type(value).__name__}.")
    if not value:
        raise UserInputError(f"{name} is required")
    return value


__all__ = ["require_nonempty"]
