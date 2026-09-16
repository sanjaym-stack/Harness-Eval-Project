# Task: Add Pagination to GET /users

Modify `app/users.py` to support pagination:
1. Support `page` (default 1) and `page_size` (default 10) query parameters.
2. Reject `page < 1` or `page_size < 1` or `page_size > 100` with HTTP 422.
3. Return response format: `{"items": [...], "total": int, "page": int, "page_size": int}`.
4. Ensure code passes ruff and mypy.
