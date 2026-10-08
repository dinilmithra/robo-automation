from robo_automation import RoboAutomationError


def test_robo_automation_error_exposes_code_details_and_dict():
    error = RoboAutomationError(
        "Navigation failed",
        code="NAVIGATION_FAILED",
        details={"url": "https://example.test"},
    )

    assert str(error) == "Navigation failed"
    assert error.code == "NAVIGATION_FAILED"
    assert error.details == {"url": "https://example.test"}
    assert error.to_dict() == {
        "type": "RoboAutomationError",
        "code": "NAVIGATION_FAILED",
        "message": "Navigation failed",
        "details": {"url": "https://example.test"},
    }
