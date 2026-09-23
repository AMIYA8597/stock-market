with open("backend/tests/integration/test_api_backtest.py", "r") as f:
    code = f.read()

replacement = """from app.models.billing import Plan, PlanEntitlement
plan = Plan(id=uuid.uuid4(), name='Premium')
shared_store[plan.id] = plan
ent = PlanEntitlement(id=uuid.uuid4(), plan_id=plan.id, feature_key='PREMIUM', is_enabled=True)
shared_store[ent.id] = ent
sub = Subscription("""

code = code.replace("sub = Subscription(", replacement)
code = code.replace("status=\"active\",\n)", "status=\"active\",\n    plan_id=plan.id,\n)")

with open("backend/tests/integration/test_api_backtest.py", "w") as f:
    f.write(code)

print("Fixed!")
