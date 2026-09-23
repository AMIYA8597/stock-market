with open('backend/app/core/events.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Add to startup_events
code = code.replace(
    '    return services',
    '    from app.core.websocket_manager import ws_manager\n    await ws_manager.startup()\n    return services'
)

# Add to shutdown_events
code = code.replace(
    '    logger.info("shutdown_tasks_cancelled")',
    '    from app.core.websocket_manager import ws_manager\n    await ws_manager.shutdown()\n    logger.info("shutdown_tasks_cancelled")'
)

with open('backend/app/core/events.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('Patched events.py')
