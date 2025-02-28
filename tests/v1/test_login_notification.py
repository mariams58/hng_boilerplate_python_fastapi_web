import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from fastapi import Request
from api.v1.models import User
from api.v1.services.login_notification import send_login_notification


@pytest.mark.asyncio
class TestSendLoginNotification:

    @patch('api.v1.services.login_notification.send_email')
    @patch('api.v1.services.login_notification.requests.get')
    async def test_send_login_notification_successful(self, mock_request_get, mock_send_email):
        # Mock user
        user = MagicMock(spec=User)
        user.email = "test@example.com"
        user.first_name = "Test"
        user.last_name = "User"

        # Mock request with headers
        request = MagicMock(spec=Request)
        request.client.host = "192.168.1.1"
        request.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "x-forwarded-for": "8.8.8.8"
        }

        # Mock IP location API response
        mock_request_get.return_value.json.return_value = {
            "city": "Mountain View",
            "country": "United States"
        }

        # Mock send_email as AsyncMock
        mock_send_email.return_value = AsyncMock()

        # Call the function
        await send_login_notification(user, request)

        # Assertions
        mock_request_get.assert_called_once_with("http://ip-api.com/json/8.8.8.8")
        mock_send_email.assert_called_once()

        # Check email parameters
        call_args = mock_send_email.call_args[1]
        assert call_args['recipient'] == "test@example.com"
        assert call_args['template_name'] == 'login-notification.html'
        assert call_args['subject'] == 'New Login to Your Account'

        # Check context variables
        context = call_args['context']
        assert context['first_name'] == "Test"
        assert context['last_name'] == "User"
        assert context['ip_address'] == "8.8.8.8"
        assert context['location'] == "Mountain View, United States"
        assert "Windows 10" in context['device']
        assert "Chrome 91" in context['device']

    @patch('api.v1.services.login_notification.send_email')
    @patch('api.v1.services.login_notification.requests.get')
    async def test_send_login_notification_local_ip(self, mock_request_get, mock_send_email):
        # Mock user
        user = MagicMock(spec=User)
        user.email = "test@example.com"
        user.first_name = "Test"
        user.last_name = "User"

        # Mock request with local IP
        request = MagicMock(spec=Request)
        request.client.host = "127.0.0.1"
        request.headers = {
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Mock send_email as AsyncMock
        mock_send_email.return_value = AsyncMock()

        # Call the function
        await send_login_notification(user, request)

        # Assertions
        mock_request_get.assert_not_called()  # Should not call IP API for local IPs
        mock_send_email.assert_called_once()

        # Check context variables
        context = mock_send_email.call_args[1]['context']
        assert context['ip_address'] == "127.0.0.1"
        assert context['location'] == "Unknown Location"
        assert "Mac OS X" in context['device']

    @patch('api.v1.services.login_notification.send_email')
    @patch('api.v1.services.login_notification.requests.get')
    async def test_send_login_notification_api_error(self, mock_request_get, mock_send_email):
        # Mock user
        user = MagicMock(spec=User)
        user.email = "test@example.com"
        user.first_name = "Test"
        user.last_name = "User"

        # Mock request
        request = MagicMock(spec=Request)
        request.client.host = "1.2.3.4"
        request.headers = {
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1",
        }

        # Mock IP API to raise exception
        mock_request_get.side_effect = Exception("API Error")

        # Mock send_email as AsyncMock
        mock_send_email.return_value = AsyncMock()

        # Call the function
        await send_login_notification(user, request)

        # Assertions
        mock_request_get.assert_called_once()
        mock_send_email.assert_called_once()

        # Check context variables
        context = mock_send_email.call_args[1]['context']
        assert context['ip_address'] == "1.2.3.4"
        assert context['location'] == "Unknown Location"
        assert "iPhone" in context['device']
        assert "iOS 14" in context['device']