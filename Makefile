SHELL := /bin/bash
VENV := .venv
PY := $(VENV)/bin/python
LOAD_ENV := set -a; [ -f lab.env ] && . ./lab.env; set +a

.PHONY: dev check wait smoke

$(PY): platform/requirements.txt platform/requirements-dev.txt
	python3.12 -m venv $(VENV)
	$(PY) -m pip install -q -r platform/requirements-dev.txt
	touch $(PY)

## Run the app on this machine with live reload against the model endpoints in lab.env
dev: $(PY)
	@$(LOAD_ENV); PYTHONPATH=platform APP_DIR=app $(PY) -m uvicorn baseapp.main:app \
		--port $${APP_PORT:-8742} --reload --reload-dir app --reload-include '*.yaml' --reload-include '*.md'

## Validate app/ and run every example against the mock model; run before every push
check: $(PY)
	@PYTHONPATH=platform APP_DIR=app PLATFORM_DIR=platform $(PY) -m baseapp.check

## Wait until your app URL serves the commit you just pushed
wait: $(PY)
	@$(LOAD_ENV); PYTHONPATH=platform $(PY) -m baseapp.wait

## Run every example against the deployed app and the real models, with timings
smoke: $(PY)
	@$(LOAD_ENV); PYTHONPATH=platform $(PY) -m baseapp.smoke
