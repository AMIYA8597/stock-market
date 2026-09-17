
path = 'app/api/v1/auth.py'
with open(path, 'r') as f:
    content = f.read()

# Add logging import
if "import logging" not in content:
    content = content.replace("import secrets", "import secrets\nimport logging\nlogger = logging.getLogger(__name__)")

# Lockout logging
content = content.replace("""        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse.create(
                code=ErrorCode.ACCOUNT_LOCKED,""", """        logger.warning(f"Auth failed: Account locked for {email} from {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse.create(
                code=ErrorCode.ACCOUNT_LOCKED,""")

# Invalid credentials logging
content = content.replace("""        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse.create(
                code=ErrorCode.INVALID_CREDENTIALS,
                message="Email or password is incorrect. Please try again.",
            ).dict(),
        )""", """        logger.warning(f"Auth failed: Invalid credentials for {email} from {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse.create(
                code=ErrorCode.INVALID_CREDENTIALS,
                message="Email or password is incorrect. Please try again.",
            ).dict(),
        )""")

# MFA required logging
content = content.replace("""        if not payload.totp_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse.create(
                    code=ErrorCode.MFA_REQUIRED,""", """        if not payload.totp_code:
            logger.warning(f"Auth failed: Missing MFA token for {email} from {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse.create(
                    code=ErrorCode.MFA_REQUIRED,""")

# MFA invalid logging
content = content.replace("""        if not totp.verify(payload.totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse.create(
                    code=ErrorCode.INVALID_CREDENTIALS,
                    message="Invalid 2FA token.",""", """        if not totp.verify(payload.totp_code):
            logger.warning(f"Auth failed: Invalid MFA token for {email} from {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse.create(
                    code=ErrorCode.INVALID_CREDENTIALS,
                    message="Invalid 2FA token.",""")

with open(path, 'w') as f:
    f.write(content)
print("Auth logging patched!")
