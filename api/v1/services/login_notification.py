from datetime import datetime

import user_agents
from user_agents.parsers import UserAgent

from fastapi import Request
from api.core.dependencies.email_sender import send_email
from api.v1.models import User
import requests


async def send_login_notification(user: User, request: Request):
    """
    Send a login notification email to the user.

    Args:
        user (User): The user who just logged in
        request (Request): The FastAPI request object
    """

    # Extract IP address from request
    ip_address = request.client.host
    if request.headers.get("x-forwarded-for"):
        ip_address = request.headers.get("x-forwarded-for").split(",")[0].strip()


    # Check if the IP is local
    if ip_address.startswith(("127.", "192.168.", "10.", "172.")):
        location = "Unknown Location"
    else:
        # Get location information via an external API
        try:
            response = requests.get(f"http://ip-api.com/json/{ip_address}").json()
            city = response.get("city", "Unknown City")
            country = response.get("country", "Unknown Country")
            location = f"{city}, {country}"
        except Exception:
            location = "Unknown Location"

    # Get user agent information
    user_agent_string = request.headers.get("user-agent", "")
    user_agent: UserAgent = user_agents.parse(user_agent_string)

    # Format device information
    device = f"{user_agent.device.family}"
    browser = f"{user_agent.browser.family} {user_agent.browser.version_string}"
    os_info = f"{user_agent.os.family} {user_agent.os.version_string}"

    if device == "Other":
        device_info = f"{os_info} - {browser}"
    else:
        device_info = f"{device} ({os_info}) - {browser}"

    change_password_link = "https://anchor-python.teams.hng.tech/change-password"
    help_center_link = "https://anchor-python.teams.hng.tech/help-center"

    # Send the notification email
    await send_email(
        recipient=user.email,
        template_name='login-notification.html',
        subject='New Login to Your Account',
        context={
            'first_name': user.first_name,
            'last_name': user.last_name,
            'login_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'ip_address': ip_address,
            'location': location,
            'device': device_info,
            'change_password_link': change_password_link,
            'help_center_link': help_center_link,
            'current_year': datetime.now().year
        }
    )