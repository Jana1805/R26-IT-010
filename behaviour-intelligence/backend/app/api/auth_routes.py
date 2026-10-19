from fastapi import APIRouter, Body, Header
from fastapi.responses import JSONResponse

from app.core import auth
from app.core.config import AUTH_ENABLED

router = APIRouter(prefix="/auth")


def _error(e: auth.AuthError) -> JSONResponse:
    return JSONResponse(status_code=e.status, content={"success": False, "detail": e.message})


def _bearer(authorization: str | None) -> str:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


@router.get("/config")
def auth_config():
    """Tells the frontend whether login is required (safety switch AUTH_ENABLED)."""
    return {"auth_enabled": AUTH_ENABLED, "roles": auth.ROLES}


@router.post("/signup")
def signup(data: dict = Body(...)):
    try:
        user = auth.create_user(data)
        token, expires = auth.issue_token(user["id"])
        return {"success": True, "message": "Account created.", "token": token, "expires_at": expires, "user": user}
    except auth.AuthError as e:
        return _error(e)


@router.post("/login")
def login(data: dict = Body(...)):
    try:
        user = auth.authenticate(data.get("email"), data.get("password"))
        token, expires = auth.issue_token(user["id"])
        return {"success": True, "message": "Logged in.", "token": token, "expires_at": expires, "user": user}
    except auth.AuthError as e:
        return _error(e)


@router.get("/me")
def me(authorization: str | None = Header(default=None)):
    try:
        return {"success": True, "user": auth.user_from_token(_bearer(authorization))}
    except auth.AuthError as e:
        return _error(e)


@router.post("/logout")
def logout(authorization: str | None = Header(default=None)):
    try:
        auth.revoke_token(_bearer(authorization))
        return {"success": True, "message": "Logged out."}
    except auth.AuthError as e:
        return _error(e)
