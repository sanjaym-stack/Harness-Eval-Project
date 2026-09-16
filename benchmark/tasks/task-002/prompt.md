# Task: Add GET /users/{user_id} with proper 404 handling

Add a new endpoint that returns a single user by ID.
1. Return the user object if found.
2. Return HTTP 404 with a clear error message if the ID doesn't exist.
3. Reject non-integer IDs with HTTP 422.
