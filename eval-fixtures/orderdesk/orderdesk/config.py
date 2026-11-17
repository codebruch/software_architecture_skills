import os

PORT = int(os.environ.get("ORDERDESK_PORT", "8080"))
DB_PATH = os.environ.get("ORDERDESK_DB", "orderdesk.db")
API_TOKEN = os.environ.get("ORDERDESK_API_TOKEN", "dev-token")
EVENTS_LOG = os.environ.get("ORDERDESK_EVENTS_LOG", "events.log")

TAX_RATE_PERCENT = 19
BULK_DISCOUNT_THRESHOLD = 10
BULK_DISCOUNT_PERCENT = 5
FREE_SHIPPING_FROM_CENTS = 50_00
SHIPPING_CENTS = 4_90

# kept for the old invoicing module
ENABLE_LEGACY_ROUNDING = False
MAX_REPORT_ROWS = 10
