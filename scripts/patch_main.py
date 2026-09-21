import re
with open("backend/app/main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add SchemaGuardMiddleware
middleware_block = "from app.core.middleware import ErrorHandlerMiddleware"
new_middleware_block = "from app.core.schema_middleware import SchemaGuardMiddleware\nfrom app.core.middleware import ErrorHandlerMiddleware"
content = content.replace(middleware_block, new_middleware_block)

app_add_middleware = "    _app.add_middleware(ErrorHandlerMiddleware)"
new_app_add_middleware = "    _app.add_middleware(SchemaGuardMiddleware)\n    _app.add_middleware(ErrorHandlerMiddleware)"
content = content.replace(app_add_middleware, new_app_add_middleware)

# Update Health Check
health_import = "    # Health check endpoint"
new_health_import = "    # Health check endpoint\n    from app.core.schema import schema_guard"
content = content.replace(health_import, new_health_import)

uptime_line = "health_status[\"uptime_seconds\"] = round(time.time() - start_time, 3)"
new_uptime_line = "schema_res = await schema_guard()\n        health_status.update(schema_res)\n        if schema_res[\"schema\"] == \"mismatch\":\n            health_status[\"status\"] = \"mismatch\"\n        " + uptime_line
content = content.replace(uptime_line, new_uptime_line)

with open("backend/app/main.py", "w", encoding="utf-8") as f:
    f.write(content)
