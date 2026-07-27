SHELL := /bin/bash

CVC5 ?= .cache/cvc5-build/bin/cvc5
PYTHON ?= .venv/bin/python

.PHONY: setup build test smoke benchmarks baseline baseline-proxy check clean

setup:
	./scripts/bootstrap.sh --tools-only

build:
	./scripts/bootstrap.sh

test:
	$(PYTHON) -m unittest discover -s tests -v

smoke: build
	$(PYTHON) scripts/run_baselines.py \
		--cvc5 $(CVC5) \
		--benchmarks benchmarks/smoke \
		--timeout 5 \
		--output benchmark-results/smoke

benchmarks:
	$(PYTHON) scripts/fetch_benchmarks.py

baseline: smoke

baseline-proxy: build benchmarks
	$(PYTHON) scripts/run_baselines.py \
		--cvc5 $(CVC5) \
		--benchmarks benchmarks/smtlib-2025 \
		--timeout 10 \
		--output benchmark-results/smtlib-2025

check: test smoke

clean:
	@echo "Generated state is under .cache/, .venv/, benchmark-results/, and benchmarks/smtlib-2025/."
	@echo "Remove those directories explicitly when a fresh build is required."

