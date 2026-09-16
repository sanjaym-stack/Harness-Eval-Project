# Candidate Agent Instructions (Defensive Engineering + MCP-Assisted)
You are an automated coding assistant adhering to strict production guidelines:
1. Input Validation: Always validate query parameters using FastAPI `Query(..., ge=1, le=100)`.
2. Explicit Schemas: Use Pydantic `BaseModel` response schemas instead of raw dictionaries.
3. Static Verification: Ensure all code passes `ruff check app/` and `mypy app/` before completing.
4. Use the `static-analysis` MCP tool (see `.mcp.json`) to auto-fix lint violations
   before finishing the task — do not rely on manual review alone.
