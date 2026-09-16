from fastapi import APIRouter

router = APIRouter()
USERS_DB = [{"id": i, "name": f"User_{i}"} for i in range(1, 101)]


@router.get("/users")
def get_users():
    """Returns unpaginated list of users."""
    return USERS_DB
