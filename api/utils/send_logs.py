import datetime
import httpx
from api.utils.settings import settings
from api.utils.logger import logger


TELEX_WEBHOOK_URL = settings.TELEX_WEBHOOK_URL


async def send_error_to_telex(request_method: str, request_url_path: str, exc):
    """send error log to telex"""
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M")

    error_data = {
        "status": "error",
        "username": "hng_boilerplate",
        "message": str(
            {
                "timestamp": timestamp,
                "event_name": "server_error",
                "request_method": request_method,
                "request_path": request_url_path,
                "status_code": 500,
                "error_message": f"An unexpected error occurred: {exc}",
            }
        ),
        "event_name": "🚨 Internal Server Error",
    }

    async with httpx.AsyncClient() as client:
        try:
            await client.post(TELEX_WEBHOOK_URL, json=error_data)
        except Exception as e:
            logger.exception(f"Failed to send error log to Telex: {e}")
