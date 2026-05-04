# Integration Tests

Integration tests are opt-in and must be marked with `@pytest.mark.integration`.

Do not add tests that place orders, spend funds, or require live credentials unless the test is explicitly documented and disabled by default.
