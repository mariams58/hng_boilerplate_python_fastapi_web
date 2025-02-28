import pytest
import datetime
from unittest.mock import AsyncMock, patch
from api.utils.send_logs import send_error_to_telex
from api.utils.settings import settings
from api.utils.logger import logger


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_send_error_to_telex_success(mock_post):
    """Test successful error logging to Telex"""

    # Mock a successful API response
    mock_post.return_value.status_code = 200

    request_method = "GET"
    request_url_path = "/test-endpoint"
    exc = "Test Exception"

    await send_error_to_telex(request_method, request_url_path, exc)

    # Get the current timestamp in the required format (YYYY-MM-DDTHH:MM)
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M")

    expected_payload = {
        "status": "error",
        "username": "hng_boilerplate",
        "message": str(
            {
                "timestamp": timestamp,  # Ensure timestamp matches format
                "event_name": "server_error",
                "request_method": request_method,
                "request_path": request_url_path,
                "status_code": 500,
                "error_message": f"An unexpected error occurred: {exc}",
            }
        ),
        "event_name": "🚨 Internal Server Error",
    }

    # Ensure that the API call was made once with correct data
    mock_post.assert_awaited_once()
    args, kwargs = mock_post.await_args
    assert args[0] == settings.TELEX_WEBHOOK_URL
    assert kwargs["json"]["username"] == expected_payload["username"]
    assert kwargs["json"]["event_name"] == expected_payload["event_name"]
    assert kwargs["json"]["message"].startswith(
        "{'timestamp': '"
    )  # Partial match to allow slight time variations


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
@patch("api.utils.logger.logger.exception")
async def test_send_error_to_telex_failure(mock_logger, mock_post):
    """Test handling failure when sending error log to Telex"""

    # Simulate an exception being raised during the HTTP request
    mock_post.side_effect = Exception("HTTP error")

    request_method = "POST"
    request_url_path = "/fail-endpoint"
    exc = "Another Test Exception"

    await send_error_to_telex(request_method, request_url_path, exc)

    # Ensure that the exception logger was called with the correct message
    mock_logger.assert_called_once_with("Failed to send error log to Telex: HTTP error")

    # Ensure the API was still attempted
    mock_post.assert_awaited_once()
