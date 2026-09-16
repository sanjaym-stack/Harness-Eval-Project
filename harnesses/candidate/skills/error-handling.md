# Skill: Defensive Resource Lookup

When implementing an endpoint that looks up a resource by ID:
1. Use a typed path parameter (`user_id: int`) so FastAPI rejects
   non-integer IDs automatically with HTTP 422 - do not accept `str`
   and cast manually.
2. If the resource is not found, raise `HTTPException(status_code=404,
   detail=...)` explicitly. Never return `None` or an empty body with
   a 200 status for a missing resource.
