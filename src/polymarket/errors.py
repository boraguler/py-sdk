"""Exception types raised by the Polymarket SDK."""


class PolymarketError(Exception):
    """Base class for errors raised by the Polymarket SDK."""


class UserInputError(PolymarketError):
    """Error raised when input fails SDK validation before a request is sent."""


class UnexpectedResponseError(PolymarketError):
    """Error raised when a response does not match the expected shape."""


class TransportError(PolymarketError):
    """Error raised when a network or runtime transport failure occurs."""


class RequestRejectedError(PolymarketError):
    """Error raised when a request receives a non-success status."""

    def __init__(self, message: str, *, status: int) -> None:
        super().__init__(message)
        self.status = status


class RateLimitError(PolymarketError):
    """Error raised when a request is rejected because of rate limits."""


class TimeoutError(PolymarketError):
    """Error raised when a wait operation exceeds its allotted polling time."""


class TransactionFailedError(PolymarketError):
    """Error raised when a submitted transaction reaches a terminal failure state."""


class CancelledSigningError(PolymarketError):
    """Error raised when the user cancels a required wallet signing action."""


class InsufficientLiquidityError(PolymarketError):
    """Error raised when resting liquidity cannot satisfy the requested execution."""


class SigningError(PolymarketError):
    """Error raised when the SDK cannot produce a signature or auth payload."""


class InsufficientAllowanceError(PolymarketError):
    """Error raised when the on-chain allowance is insufficient for the order amount."""
