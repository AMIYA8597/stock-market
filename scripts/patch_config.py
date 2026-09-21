import re
with open("backend/app/core/config.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix env_file
content = re.sub(r'env_file=\("\.env", "\.env\.example"\)', 'env_file=".env"', content)

# Replace Database block
db_block_pattern = re.compile(r"# \S+ Database \S+\n\s+DATABASE_URL: str = Field\(.*?\n\s+DATABASE_POOL_RECYCLE: int = Field\(\n\s+default=3600, description=\"Recycle connections after N seconds \(for connection pooling\)\"\n\s+\)", re.DOTALL)
new_db_block = """# \u2500\u2500\u2500 Database \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    DATABASE_URL: str = Field(
        default="",
        description="Runtime DB URL for API (role nq_api)",
    )
    MIGRATIONS_DATABASE_URL: str = Field(
        default="", description="DB URL for Alembic migrations (role nq_migrator)"
    )
    INGEST_DATABASE_URL: str = Field(
        default="", description="DB URL for market data jobs (role nq_ingest)"
    )
    DB_POOL_MODE: str = Field(
        default="session", description="Connection pool mode: 'session' or 'transaction'"
    )
    DB_POOL_SIZE: int = Field(default=5, description="SQLAlchemy connection pool size")
    DB_MAX_OVERFLOW: int = Field(
        default=2, description="Maximum connections to overflow"
    )
    DB_POOL_RECYCLE: int = Field(
        default=1800, description="Recycle connections after N seconds"
    )
    DB_SSL_REQUIRED: bool = Field(default=True, description="Require SSL for DB connection")"""
content = db_block_pattern.sub(new_db_block, content)

# Add startup validator
validator_code = """
    @model_validator(mode="after")
    def validate_database_user(self) -> Settings:
        if self.ENVIRONMENT != "test":
            if "postgres:" in self.DATABASE_URL.lower():
                if self.ENVIRONMENT == "production":
                    raise ValueError("Cannot run as postgres superuser in production. Use nq_api role.")
        return self
"""
content = content.replace("    @model_validator(mode=\"after\")\n    def validate_production_keys(self) -> Settings:", validator_code + "\n    @model_validator(mode=\"after\")\n    def validate_production_keys(self) -> Settings:")

# Remove DATABASE_URL_SYNC property
sync_pattern = re.compile(r"    @property\n    def DATABASE_URL_SYNC\(self\) -> str:.*?(?=\n\n#)", re.DOTALL)
content = sync_pattern.sub("", content)

# Simplify get_settings
get_settings_pattern = re.compile(r"def get_settings\(\) -> Settings:.*?return Settings\(\)", re.DOTALL)
new_get_settings = """def get_settings() -> Settings:
    import os
    env_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    if os.path.exists(env_file):
        return Settings(_env_file=env_file)
    return Settings()"""
content = get_settings_pattern.sub(new_get_settings, content)

with open("backend/app/core/config.py", "w", encoding="utf-8") as f:
    f.write(content)
