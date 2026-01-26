"""
============================================================
           AI DATA ANALYST PRO - CONFIGURATION
============================================================
Central configuration file for all app settings.
Use environment variables for sensitive data in production.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================
#                    APP SETTINGS
# ============================================================

APP_NAME = "AI Data Analyst Pro"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Sukumar Jujjuvarapu"

# ============================================================
#                    API KEYS
# ============================================================

# Groq API Key (for LLM)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "your-groq-api-key-here")

# OpenAI API Key (optional backup)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ============================================================
#                    STRIPE CONFIGURATION
# ============================================================

# Stripe Keys - Get from https://dashboard.stripe.com/apikeys
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_YOUR_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "pk_test_YOUR_KEY")

# Stripe Price IDs - Create products at https://dashboard.stripe.com/products
STRIPE_PRICES = {
    "starter_monthly": os.getenv("STRIPE_PRICE_STARTER_MONTHLY", "price_xxxxx"),
    "starter_yearly": os.getenv("STRIPE_PRICE_STARTER_YEARLY", "price_xxxxx"),
    "pro_monthly": os.getenv("STRIPE_PRICE_PRO_MONTHLY", "price_xxxxx"),
    "pro_yearly": os.getenv("STRIPE_PRICE_PRO_YEARLY", "price_xxxxx"),
    "enterprise_monthly": os.getenv("STRIPE_PRICE_ENTERPRISE_MONTHLY", "price_xxxxx"),
    "enterprise_yearly": os.getenv("STRIPE_PRICE_ENTERPRISE_YEARLY", "price_xxxxx"),
}

# Stripe Webhook Secret - Get from webhook settings
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_xxxxx")

# ============================================================
#                    DATABASE PATHS
# ============================================================

# Application database (users, history, etc.)
APP_DB_PATH = os.getenv("APP_DB_PATH", "app_database.db")

# Default sample database for demo
DEFAULT_SAMPLE_DB = os.getenv("DEFAULT_SAMPLE_DB", "Chinook_Sqlite.sqlite")

# Upload directory
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

# ============================================================
#                    SUBSCRIPTION TIERS
# ============================================================

SUBSCRIPTION_TIERS = {
    "free": {
        "name": "Free",
        "price_monthly": 0,
        "price_yearly": 0,
        "queries_per_day": 5,
        "file_types": ["csv"],
        "max_file_size_mb": 5,
        "history_enabled": False,
        "pdf_export": False,
        "priority_support": False,
    },
    "starter": {
        "name": "Starter",
        "price_monthly": 9,
        "price_yearly": 90,
        "queries_per_day": 50,
        "file_types": ["csv", "xlsx", "xls"],
        "max_file_size_mb": 25,
        "history_enabled": True,
        "pdf_export": False,
        "priority_support": False,
    },
    "pro": {
        "name": "Pro",
        "price_monthly": 29,
        "price_yearly": 290,
        "queries_per_day": 500,
        "file_types": ["csv", "xlsx", "xls", "sqlite", "db"],
        "max_file_size_mb": 100,
        "history_enabled": True,
        "pdf_export": True,
        "priority_support": False,
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": 99,
        "price_yearly": 990,
        "queries_per_day": 99999,
        "file_types": ["csv", "xlsx", "xls", "sqlite", "db", "json"],
        "max_file_size_mb": 500,
        "history_enabled": True,
        "pdf_export": True,
        "priority_support": True,
    },
}

# ============================================================
#                    LLM SETTINGS
# ============================================================

# Default model for SQL generation
DEFAULT_LLM_MODEL = "llama-3.3-70b-versatile"

# Backup models
BACKUP_LLM_MODELS = [
    "llama3-70b-8192",
    "mixtral-8x7b-32768",
]

# Model temperature (0 = deterministic, 1 = creative)
LLM_TEMPERATURE = 0.1

# Max tokens for response
LLM_MAX_TOKENS = 1000

# ============================================================
#                    SECURITY SETTINGS
# ============================================================

# Session expiry (hours)
SESSION_EXPIRY_HOURS = 24

# Password requirements
MIN_PASSWORD_LENGTH = 6

# Rate limiting
MAX_REQUESTS_PER_MINUTE = 30

# Allowed SQL commands (for security)
ALLOWED_SQL_COMMANDS = ["SELECT"]
BLOCKED_SQL_COMMANDS = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE"]

# ============================================================
#                    EMAIL SETTINGS (Optional)
# ============================================================

# For password reset, notifications, etc.
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@yourdomain.com")

# ============================================================
#                    DEPLOYMENT SETTINGS
# ============================================================

# Base URL (update for production)
BASE_URL = os.getenv("BASE_URL", "http://localhost:8501")

# Debug mode
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# ============================================================
#                    HELPER FUNCTIONS
# ============================================================

def get_tier_config(tier_name: str) -> dict:
    """Get configuration for a specific tier"""
    return SUBSCRIPTION_TIERS.get(tier_name, SUBSCRIPTION_TIERS["free"])

def get_query_limit(tier_name: str) -> int:
    """Get daily query limit for a tier"""
    return get_tier_config(tier_name)["queries_per_day"]

def get_allowed_file_types(tier_name: str) -> list:
    """Get allowed file types for a tier"""
    return get_tier_config(tier_name)["file_types"]

def is_feature_enabled(tier_name: str, feature: str) -> bool:
    """Check if a feature is enabled for a tier"""
    config = get_tier_config(tier_name)
    return config.get(feature, False)
