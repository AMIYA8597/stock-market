import os
import sys
import sqlite3
import psycopg2
from psycopg2.extras import DictCursor

def get_orm_tables():
    # Attempt to import SQLAlchemy models and get metadata
    try:
        sys.path.insert(0, os.path.abspath("backend"))
        from app.database.connection import Base
        # Note: Depending on where models are imported, we might need to import them all
        # A quick hack is to import the main app or import models explicitly
        # We will try to scan the models directory
        import glob
        import importlib
        models_dir = os.path.join("backend", "app", "models")
        for f in glob.glob(os.path.join(models_dir, "*.py")):
            module_name = os.path.basename(f)[:-3]
            if module_name != "__init__":
                importlib.import_module(f"app.models.{module_name}")
                
        return set(Base.metadata.tables.keys())
    except Exception as e:
        print(f"Error loading ORM tables: {e}")
        return set()

def inventory_postgres(db_url):
    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(db_url, connect_timeout=5)
    print("Connected!")
    cur = conn.cursor(cursor_factory=DictCursor)
    
    inventory = []
    inventory.append("# PostgreSQL Inventory")
    
    # 1. Version
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    inventory.append(f"\n## Version\n`{version}`\n")
    
    # 2. Extensions
    cur.execute("SELECT extname, extversion FROM pg_extension;")
    exts = cur.fetchall()
    inventory.append("## Installed Extensions")
    for e in exts:
        inventory.append(f"- {e['extname']} (v{e['extversion']})")
    inventory.append("")
    
    # 3. Schemas
    cur.execute("SELECT schema_name FROM information_schema.schemata;")
    schemas = cur.fetchall()
    inventory.append("## Schemas")
    for s in schemas:
        inventory.append(f"- {s['schema_name']}")
    inventory.append("")
    
    # 4. Tables in public
    cur.execute("""
        SELECT c.relname, c.reltuples::bigint AS row_count,
               pg_size_pretty(pg_total_relation_size(c.oid)) AS size,
               c.relrowsecurity,
               r.rolname AS owner
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_roles r ON r.oid = c.relowner
        WHERE n.nspname = 'public' AND c.relkind = 'r'
        ORDER BY c.relname;
    """)
    tables = cur.fetchall()
    db_tables = set([t['relname'] for t in tables])
    
    inventory.append("## Tables (public)")
    inventory.append("| Table | Row Count | Size | RLS Enabled | Owner |")
    inventory.append("|---|---|---|---|---|")
    for t in tables:
        inventory.append(f"| {t['relname']} | {t['row_count']} | {t['size']} | {t['relrowsecurity']} | {t['owner']} |")
    inventory.append("")
    
    # 5. Alembic version
    if 'alembic_version' in db_tables:
        cur.execute("SELECT version_num FROM alembic_version;")
        alembic_versions = [row['version_num'] for row in cur.fetchall()]
        inventory.append(f"## Alembic Version\n`{alembic_versions}`\n")
    else:
        inventory.append("## Alembic Version\n`No alembic_version table found`\n")
        
    # 6. ORM vs DB
    orm_tables = get_orm_tables()
    inventory.append("## DB vs ORM Differences")
    if orm_tables:
        in_db_not_orm = db_tables - orm_tables
        in_orm_not_db = orm_tables - db_tables
        
        inventory.append(f"- **In DB, not in ORM:** {in_db_not_orm if in_db_not_orm else 'None'}")
        inventory.append(f"- **In ORM, not in DB:** {in_orm_not_db if in_orm_not_db else 'None'}")
    else:
        inventory.append("- *Failed to load ORM tables or no ORM tables found.*")
    inventory.append("")
    
    # 7. Indexes
    cur.execute("""
        SELECT tablename, indexname, indexdef 
        FROM pg_indexes 
        WHERE schemaname = 'public' 
        ORDER BY tablename, indexname;
    """)
    indexes = cur.fetchall()
    inventory.append("## Indexes")
    for i in indexes:
        inventory.append(f"- **{i['tablename']}**: {i['indexname']}")
    inventory.append("")
    
    # 8. Roles and privileges
    roles_to_check = ['anon', 'authenticated', 'service_role', 'postgres']
    roles_str = "','".join(roles_to_check)
    cur.execute(f"""
        SELECT grantee, table_name, privilege_type
        FROM information_schema.role_table_grants
        WHERE table_schema = 'public' AND grantee IN ('{roles_str}')
        ORDER BY grantee, table_name;
    """)
    grants = cur.fetchall()
    inventory.append("## Roles and Privileges on Public Tables")
    inventory.append("| Role | Table | Privilege |")
    inventory.append("|---|---|---|")
    for g in grants:
        inventory.append(f"| {g['grantee']} | {g['table_name']} | {g['privilege_type']} |")
    inventory.append("")
    
    # 9. Timescaledb, pg_cron, pg_net
    ext_names = [e['extname'] for e in exts]
    inventory.append("## Specific Capabilities Availability")
    inventory.append(f"- **timescaledb:** {'Installed' if 'timescaledb' in ext_names else 'Not Installed'}")
    inventory.append(f"- **pg_cron:** {'Installed' if 'pg_cron' in ext_names else 'Not Installed'}")
    inventory.append(f"- **pg_net:** {'Installed' if 'pg_net' in ext_names else 'Not Installed'}")
    inventory.append("")
    
    conn.close()
    return "\n".join(inventory)

def inventory_sqlite(db_path):
    inventory = []
    inventory.append("# SQLite Inventory (`backend/dev.db`)")
    if not os.path.exists(db_path):
        inventory.append("*Database file does not exist.*")
        return "\n".join(inventory)
        
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cur.fetchall()
    
    inventory.append("## Tables")
    inventory.append("| Table | Row Count |")
    inventory.append("|---|---|")
    
    worth_migrating = False
    migratable_tables = []
    for t in tables:
        table_name = t[0]
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cur.fetchone()[0]
            inventory.append(f"| {table_name} | {count} |")
            if count > 0 and table_name not in ('alembic_version', 'sqlite_sequence'):
                migratable_tables.append(f"{table_name} ({count} rows)")
                worth_migrating = True
        except Exception:
            inventory.append(f"| {table_name} | ERROR |")
            
    inventory.append("\n## Migration Recommendation")
    if worth_migrating:
        inventory.append(f"**Recommendation:** The local database contains data in: {', '.join(migratable_tables)}. ")
        inventory.append("Evaluate whether these tables contain essential data like actual users or subscriptions that must be preserved. If they are just dummy/seed data, do NOT migrate them.")
    else:
        inventory.append("**Recommendation:** No significant data found. DO NOT migrate anything from SQLite.")
        
    conn.close()
    return "\n".join(inventory)

def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set.")
        sys.exit(1)
        
    # Replace asyncpg dialect with psycopg2 for this script
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        if "?" not in db_url and "supabase" in db_url:
            db_url += "?sslmode=require"
        
    docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../docs/stage1"))
    os.makedirs(docs_dir, exist_ok=True)
    
    out = []
    try:
        out.append(inventory_postgres(db_url))
    except Exception as e:
        out.append(f"# PostgreSQL Inventory\nFailed to connect/inventory: {e}")
        
    out.append("\n---\n")
    
    try:
        sqlite_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend/dev.db"))
        out.append(inventory_sqlite(sqlite_path))
    except Exception as e:
        out.append(f"# SQLite Inventory\nFailed to connect/inventory: {e}")
        
    out.append("\n---\n")
    out.append("# Advisor Reports (Supabase Dashboard)")
    out.append("*Paste Security and Performance Advisor reports here.*")
    
    out_file = os.path.join(docs_dir, "BASELINE_DB.md")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
        
    print(f"Created {out_file}")

if __name__ == "__main__":
    main()
