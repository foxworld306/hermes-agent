# Cyan Agent Phase 1 Issues / Blockers

## Current Blockers
None yet

## Resolved Issues
- `_sanitize_user_id` correctly converts `/` to `_` on Windows (plan test expected `/` to survive, but it's unsafe for filesystem)
- pytest addopts in pyproject.toml has `-n` flag requiring xdist; use `-o addopts=` to bypass on Windows without xdist

## Warnings
- Task 10 brand rename touches core files - be careful with user-facing strings
- Docker build requires .[all] extras in pyproject.toml
- AIAgent instantiation may fail if config incomplete - wrap in try/except
