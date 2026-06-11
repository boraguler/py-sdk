from polymarket.rfq import RfqErrorCode


def test_balance_and_reservation_rfq_error_codes_are_supported() -> None:
    assert RfqErrorCode("ALLOWANCE_VALIDATION_FAILED") is RfqErrorCode.ALLOWANCE_VALIDATION_FAILED
    assert RfqErrorCode("BALANCE_VALIDATION_FAILED") is RfqErrorCode.BALANCE_VALIDATION_FAILED
    assert (
        RfqErrorCode("PRE_EXECUTION_BALANCE_RESERVATION_FAILED")
        is RfqErrorCode.PRE_EXECUTION_BALANCE_RESERVATION_FAILED
    )
