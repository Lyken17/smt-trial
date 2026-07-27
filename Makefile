SHELL := /bin/bash

CVC5 ?= .cache/cvc5-build/bin/cvc5
PYTHON ?= .venv/bin/python
SCORE_ARGS ?=

.PHONY: setup build rebuild test smoke score check clean distclean

setup:
	./scripts/bootstrap.sh --tools-only

build:
	@if [[ -x "$(CVC5)" ]]; then \
		"$(CVC5)" --version | head -1; \
	else \
		./scripts/bootstrap.sh; \
	fi

rebuild:
	./scripts/bootstrap.sh

test:
	$(PYTHON) -m unittest discover -s tests -v

smoke:
	$(PYTHON) tests/submission_tests.py \
		--cvc5 $(CVC5) \
		--benchmarks benchmarks/smoke \
		--timeout 5

score:
	$(PYTHON) tests/submission_tests.py \
		--cvc5 $(CVC5) \
		--benchmarks benchmarks/smtlib-2025 \
		--timeout 10 \
		$(SCORE_ARGS)

check: test smoke

clean:
	find . -maxdepth 1 -type d -name __pycache__ \
		-exec find {} -depth -delete \;
	find aws-build cvc5_cloud scripts tests -type d -name __pycache__ \
		-prune -exec find {} -depth -delete \;
	find . -maxdepth 1 -type d \
		\( -name .pytest_cache -o -name test-results \) \
		-exec find {} -depth -delete \;

distclean: clean
	find . -maxdepth 1 -type d \( -name .cache -o -name .venv \) \
		-exec find {} -depth -delete \;
