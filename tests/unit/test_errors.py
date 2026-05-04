from polymarket import (
    CancelledSigningError,
    InsufficientLiquidityError,
    PolymarketError,
    RateLimitError,
    RequestRejectedError,
    SigningError,
    TimeoutError,
    TransactionFailedError,
    TransportError,
    UnexpectedResponseError,
    UserInputError,
)


def test_error_hierarchy_matches_public_sdk_errors() -> None:
    error_classes = [
        UserInputError,
        UnexpectedResponseError,
        TransportError,
        RequestRejectedError,
        RateLimitError,
        TimeoutError,
        TransactionFailedError,
        CancelledSigningError,
        InsufficientLiquidityError,
        SigningError,
    ]

    for error_class in error_classes:
        assert issubclass(error_class, PolymarketError)


def test_sdk_errors_support_idiomatic_isinstance_checks() -> None:
    assert isinstance(RateLimitError("rate limited"), PolymarketError)
    assert not isinstance(ValueError("plain error"), PolymarketError)


def test_request_rejected_error_exposes_status() -> None:
    error = RequestRejectedError("rejected", status=400)

    assert str(error) == "rejected"
    assert error.status == 400
