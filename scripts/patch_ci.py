import re
with open(".github/workflows/ci.yml", "r", encoding="utf-8") as f:
    content = f.read()

migrations_job = """  migrations:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:17-alpine
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: changeme
          POSTGRES_DB: nq_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    env:
      MIGRATIONS_DATABASE_URL: postgresql+psycopg2://postgres:changeme@localhost:5432/nq_test
      DATABASE_URL: postgresql+asyncpg://postgres:changeme@localhost:5432/nq_test
      REDIS_URL: redis://localhost:6379
      IS_PRODUCTION: false
      SUPABASE_URL: http://localhost:8000
      SUPABASE_SERVICE_KEY: dummy
      JWT_SECRET: dummy
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Set up Python
        run: ~/.local/bin/uv python install 3.12
      - name: Install dependencies
        working-directory: ./backend
        run: ~/.local/bin/uv sync
      - name: Test migrations lifecycle
        working-directory: ./backend
        run: |
          ~/.local/bin/uv run alembic upgrade head
          ~/.local/bin/uv run alembic check
          ~/.local/bin/uv run alembic downgrade base
          ~/.local/bin/uv run alembic upgrade head
      - name: Run schema tests
        working-directory: ./backend
        run: ~/.local/bin/uv run pytest tests/integration/test_schema.py -q"""

content = re.sub(r"  migrations:.*?(?=\n  web:)", migrations_job + "\n", content, flags=re.DOTALL)

with open(".github/workflows/ci.yml", "w", encoding="utf-8") as f:
    f.write(content)
