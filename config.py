"""Configuration module for Telegram VPN Bot."""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# x-ui Panel Configuration
XUI_URL = os.getenv("XUI_URL", "").rstrip("/")
XUI_USERNAME = os.getenv("XUI_USERNAME", "admin")
XUI_PASSWORD = os.getenv("XUI_PASSWORD", "admin")
# Subscription URL configuration (usually different port from panel)
XUI_SUBSCRIPTION_HOST = os.getenv("XUI_SUBSCRIPTION_HOST", "")  # e.g., 194.87.125.20:2096
XUI_SUBSCRIPTION_PORT = os.getenv("XUI_SUBSCRIPTION_PORT", "")  # e.g., 2096

# Default User Settings
DEFAULT_PROTOCOL = os.getenv("DEFAULT_PROTOCOL", "vmess")
DEFAULT_EXPIRY_DAYS = int(os.getenv("DEFAULT_EXPIRY_DAYS", "30"))
DEFAULT_TOTAL_GB = int(os.getenv("DEFAULT_TOTAL_GB", "100"))
# Optional: specify inbound ID to use (if not set, will try to find automatically)
DEFAULT_INBOUND_ID_STR = os.getenv("DEFAULT_INBOUND_ID", "")
DEFAULT_INBOUND_ID = int(DEFAULT_INBOUND_ID_STR) if DEFAULT_INBOUND_ID_STR else None

# Web App Configuration (for copy button functionality)
# Set this to your GitHub Pages URL or any HTTPS URL where copy_subscription.html is hosted
# Example: https://yourusername.github.io/vpn-bot-web-app/index.html
WEB_APP_URL = os.getenv("WEB_APP_URL", "")  # URL to web app (e.g., https://yourusername.github.io/vpn-bot-web-app/index.html)

# Validate required configuration
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is required in .env file")

if not XUI_URL:
    raise ValueError("XUI_URL is required in .env file")

