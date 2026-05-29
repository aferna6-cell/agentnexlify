# Agent OS — common tasks.
.PHONY: help install demo route interactive api test clean

help:
	@echo "Agent OS targets:"
	@echo "  make install      install runtime + test deps"
	@echo "  make demo         run the terminal walkthrough (all routing paths)"
	@echo "  make route q=...  route a single ask, e.g. make route q='text Mike a reminder'"
	@echo "  make interactive  start the REPL demo"
	@echo "  make api          serve the API + web client on http://localhost:8000"
	@echo "  make test         run the test suite"
	@echo "  make clean        remove caches and build artifacts"

install:
	pip install -r requirements.txt

demo:
	python -m agent_os.demo.cli

# Usage: make route q="follow up with Mike on the $$1,100 quote"
route:
	python -m agent_os.demo.cli "$(q)"

interactive:
	python -m agent_os.demo.cli --interactive

api:
	uvicorn agent_os.api.app:app --reload --port 8000

test:
	python -m pytest -q

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
