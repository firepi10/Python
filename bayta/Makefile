SHELL := /bin/bash
VENV := backend/.venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: install test lint typecheck build dev screenshot seed clean

install:
	python3 -m venv $(VENV)
	$(PIP) install -q --upgrade pip
	$(PIP) install -q -e "backend[dev]" || (cd backend && ../$(PIP) install -q -e ".[dev]")
	cd frontend && npm install --no-audit --no-fund

test:
	cd backend && .venv/bin/pytest -q

lint:
	cd backend && .venv/bin/ruff check app tests

typecheck:
	cd frontend && npm run typecheck

build:
	cd frontend && npm run build

dev:
	./scripts/dev.sh

seed:
	cd backend && .venv/bin/python ../scripts/seed_demo.py

screenshot: build
	cd frontend && node ../scripts/screenshot.mjs

clean:
	rm -rf backend/.venv frontend/node_modules frontend/dist artifacts
