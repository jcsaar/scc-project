.PHONY: backend-test

backend-test:
	cd backend && uv run pytest -q

