import os


def process_file(filepath):
    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    new_content = content.replace('current_user.get("sub")', 'str(current_user.id)')
    new_content = new_content.replace('current_user.get("role")', 'current_user.role')
    new_content = new_content.replace('current_user.get("user_id")', 'str(current_user.id)')
    new_content = new_content.replace('current_user.get("jti")', 'None')

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Updated {filepath}')

for root, _, files in os.walk('app'):
    for file in files:
        if file.endswith('.py'):
            process_file(os.path.join(root, file))
