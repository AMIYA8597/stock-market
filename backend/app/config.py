import os

class Config:
    """Application configuration settings"""
    # Flask settings
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    TESTING = os.getenv('FLASK_TESTING', 'false').lower() == 'true'

    # Database URI (SQLite by default, can be overridden)
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///stock_market.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # API keys for data sources (free tiers)
    ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', '')
    # No key needed for Indian-Stock-Market-API or yfinance

    # Cache settings
    CACHE_TYPE = 'simple'  # In-memory cache, can be switched to Redis
    CACHE_DEFAULT_TIMEOUT = 300  # seconds
