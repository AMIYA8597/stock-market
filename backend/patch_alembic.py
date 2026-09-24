import re
with open('alembic/versions/a5328e632291_add_missing_part_2_tables.py', 'r') as f:
    content = f.read()

rls_code = """    # ### end Alembic commands ###

    # Set up RLS
    for table in ["alerts", "alert_events"]:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(
            f"CREATE POLICY system_all ON {table} FOR ALL "
            f"USING (current_setting('app.is_system', true) = 'true') "
            f"WITH CHECK (current_setting('app.is_system', true) = 'true');"
        )
    # Organization read policies
    op.execute("CREATE POLICY select_own_org_alerts ON alerts FOR SELECT USING (organization_id IN (SELECT organization_id FROM org_members WHERE user_id = NULLIF(current_setting('request.jwt.claim.sub', true), '')::uuid));")
    op.execute("CREATE POLICY select_own_org_events ON alert_events FOR SELECT USING (organization_id IN (SELECT organization_id FROM org_members WHERE user_id = NULLIF(current_setting('request.jwt.claim.sub', true), '')::uuid));")
"""

content = content.replace("    # ### end Alembic commands ###", rls_code, 1)

with open('alembic/versions/a5328e632291_add_missing_part_2_tables.py', 'w') as f:
    f.write(content)
