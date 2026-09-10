.PHONY: demo test backend-test frontend-test build verify-secrets e2e migrate seed

demo:
	./scripts/dev.sh

test: backend-test frontend-test

backend-test:
	cd backend && .venv/bin/python -m pytest -q

frontend-test:
	cd frontend && npm test

build:
	cd backend && .venv/bin/python -m compileall -q app
	cd frontend && npm run build

verify-secrets:
	backend/.venv/bin/python scripts/verify_no_secret_egress.py

e2e:
	cd frontend && npm run e2e

migrate:
	cd backend && .venv/bin/alembic upgrade head

seed:
	backend/.venv/bin/python scripts/seed_demo.py
