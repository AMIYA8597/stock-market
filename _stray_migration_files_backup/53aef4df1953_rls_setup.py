"""RLS Setup

Revision ID: 53aef4df1953
Revises: 53aef4df1952
Create Date: 2026-09-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '53aef4df1953'
down_revision = '53aef4df1952'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Set up RLS on users, portfolios, orders
    op.execute("""
    -- Enable RLS
    ALTER TABLE users ENABLE ROW LEVEL SECURITY;
    ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;
    ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

    -- Drop existing policies if any
    DROP POLICY IF EXISTS "Users can view and edit their own profile" ON users;
    DROP POLICY IF EXISTS "Celery can access all users" ON users;
    
    DROP POLICY IF EXISTS "Users can view their own portfolios" ON portfolios;
    DROP POLICY IF EXISTS "Celery can access all portfolios" ON portfolios;
    
    DROP POLICY IF EXISTS "Users can view their own orders" ON orders;
    DROP POLICY IF EXISTS "Celery can access all orders" ON orders;

    -- Users policies
    CREATE POLICY "Users can view and edit their own profile"
    ON users
    FOR ALL
    USING (auth_id = current_setting('request.jwt.claim.sub', true))
    WITH CHECK (auth_id = current_setting('request.jwt.claim.sub', true));

    CREATE POLICY "Celery can access all users"
    ON users
    FOR ALL
    USING (current_setting('app.is_system', true) = 'true');

    -- Portfolios policies
    CREATE POLICY "Users can view their own portfolios"
    ON portfolios
    FOR ALL
    USING (user_id::text = current_setting('request.jwt.claim.sub', true))
    WITH CHECK (user_id::text = current_setting('request.jwt.claim.sub', true));

    CREATE POLICY "Celery can access all portfolios"
    ON portfolios
    FOR ALL
    USING (current_setting('app.is_system', true) = 'true');

    -- Orders policies
    CREATE POLICY "Users can view their own orders"
    ON orders
    FOR ALL
    USING (user_id::text = current_setting('request.jwt.claim.sub', true))
    WITH CHECK (user_id::text = current_setting('request.jwt.claim.sub', true));

    CREATE POLICY "Celery can access all orders"
    ON orders
    FOR ALL
    USING (current_setting('app.is_system', true) = 'true');
    """)

def downgrade() -> None:
    op.execute("""
    DROP POLICY IF EXISTS "Users can view and edit their own profile" ON users;
    DROP POLICY IF EXISTS "Celery can access all users" ON users;
    
    DROP POLICY IF EXISTS "Users can view their own portfolios" ON portfolios;
    DROP POLICY IF EXISTS "Celery can access all portfolios" ON portfolios;
    
    DROP POLICY IF EXISTS "Users can view their own orders" ON orders;
    DROP POLICY IF EXISTS "Celery can access all orders" ON orders;

    ALTER TABLE users DISABLE ROW LEVEL SECURITY;
    ALTER TABLE portfolios DISABLE ROW LEVEL SECURITY;
    ALTER TABLE orders DISABLE ROW LEVEL SECURITY;
    """)
