SHELL := /bin/bash
PYTHON ?= .venv/bin/python
SMTCOMP ?= .venv/bin/smtcomp
TRACK ?= SingleQuery
DIVISION ?=
SETUP_CONFIG ?= configs/setup-single-query.env
DOWNLOAD_JOBS ?= 1
DOWNLOAD_SEGMENTS ?= 8
EXTRACT_JOBS ?= 4

TRACK_KIND_SingleQuery := 24
TRACK_KIND_Incremental := par
TRACK_KIND_UnsatCore := par
TRACK_KIND_ModelValidation := par
TRACK_KIND_Parallel := par
PERFORMANCE ?= $(TRACK_KIND_$(TRACK))
KIND ?= $(PERFORMANCE)
RUN_ID ?= $(TRACK)$(if $(strip $(DIVISION)),-$(DIVISION),)-$(PERFORMANCE)

TRACK_SELECTION_SingleQuery := .cache/execution/benchmarks/files
TRACK_SELECTION_Incremental := .cache/execution/benchmarks/files_inc
TRACK_SELECTION_UnsatCore := .cache/execution/benchmarks/files_unsatcore
TRACK_SELECTION_ModelValidation := .cache/execution/benchmarks/files_model
TRACK_SELECTION_Parallel := .cache/execution/benchmarks/files_parallel
TRACK_RESULTS_SingleQuery = results/$(RUN_ID)/results_singlequery
TRACK_RESULTS_Incremental = results/$(RUN_ID)/results_inc
TRACK_RESULTS_UnsatCore = results/$(RUN_ID)/results_unsatcore
TRACK_RESULTS_ModelValidation = results/$(RUN_ID)/results_model
TRACK_RESULTS_Parallel = results/$(RUN_ID)/results_parallel
TRACK_CVC5_SingleQuery := .cache/solver/default/bin/cvc5
TRACK_CVC5_Incremental := .cache/solver/incremental/bin/cvc5
TRACK_CVC5_UnsatCore := .cache/solver/default/bin/cvc5
TRACK_CVC5_ModelValidation := .cache/solver/default/bin/cvc5
TRACK_CVC5_Parallel := .cache/solver/default/bin/cvc5

CONFIG ?= configs/cvc5/$(TRACK)/$(PERFORMANCE).toml
SELECTION ?= $(TRACK_SELECTION_$(TRACK))
RESULTS ?= $(TRACK_RESULTS_$(TRACK))
CVC5 ?= $(TRACK_CVC5_$(TRACK))
XML ?= work/cvc5-$(TRACK)$(if $(strip $(DIVISION)),-$(DIVISION)-$(PERFORMANCE),).xml
TRACE_EXECUTOR ?= .cache/execution/smtlib2_trace_executor
UC_VALIDATION_MODE ?= external
DIVISION_ARG := $(if $(strip $(DIVISION)),--division $(DIVISION),)
UC_VALIDATION_RESULTS := $(dir $(RESULTS))unsat_core_validation_results
UC_VALIDATOR_CACHE := .cache/execution
UC_VALIDATOR_MANIFEST := work/unsat-core-validator-pool.json

.PHONY: system-deps storage-single-query setup setup-single-query metadata benchmarks benchmarks-single-query \
	solver solver-single-query cache select select-single-query select-all execution-tools model-validator \
	prepare run validate-model validate-unsat-core generate-unsat-core-validation \
	manifest-unsat-core-validator-pool build-unsat-core-validator-pool \
	run-unsat-core-validator-pool run-unsat-core-validator \
	merge-unsat-core-validation init-configs score score-overall score-matrix score-24 score-parallel clean

system-deps:
	bash scripts/install_system_deps.sh $(SETUP_CONFIG)

storage-single-query:
	bash scripts/prepare_storage.sh $(SETUP_CONFIG)

setup:
	bash scripts/bootstrap.sh

init-configs:
	$(PYTHON) scripts/init_track_configs.py --track $(TRACK)

# Sequential on purpose: each stage consumes the artefacts produced by the previous one.
setup-single-query:
	$(MAKE) system-deps SETUP_CONFIG=$(SETUP_CONFIG)
	$(MAKE) storage-single-query SETUP_CONFIG=$(SETUP_CONFIG)
	$(MAKE) setup
	$(MAKE) benchmarks-single-query SETUP_CONFIG=$(SETUP_CONFIG)
	$(MAKE) solver-single-query SETUP_CONFIG=$(SETUP_CONFIG)
	$(MAKE) cache
	$(MAKE) select-single-query

metadata:
	$(PYTHON) scripts/fetch_official.py metadata

benchmarks:
	$(PYTHON) scripts/fetch_official.py benchmarks

benchmarks-single-query: storage-single-query
	@set -a; source $(SETUP_CONFIG); set +a; \
		DOWNLOAD_JOBS=$(DOWNLOAD_JOBS) DOWNLOAD_SEGMENTS=$(DOWNLOAD_SEGMENTS) \
		EXTRACT_JOBS=$(EXTRACT_JOBS) \
		$(PYTHON) scripts/fetch_official.py "$$BENCHMARK_COMPONENT"

solver:
	$(PYTHON) scripts/fetch_official.py solver

solver-single-query:
	@set -a; source $(SETUP_CONFIG); set +a; \
		$(PYTHON) scripts/fetch_official.py "$$SOLVER_COMPONENT"

cache: metadata
	$(SMTCOMP) create-cache .cache/official/data

select: cache benchmarks
	bash scripts/select_track.sh $(TRACK)

select-single-query: cache benchmarks-single-query
	bash scripts/select_track.sh SingleQuery

select-all: cache benchmarks
	bash scripts/select_track.sh SingleQuery
	bash scripts/select_track.sh Incremental
	bash scripts/select_track.sh ModelValidation
	bash scripts/select_track.sh UnsatCore
	bash scripts/select_track.sh Parallel

execution-tools:
	@if [[ ! -x "$(TRACE_EXECUTOR)" ]]; then $(SMTCOMP) prepare-execution .cache/execution; fi
	@source versions.env; \
		echo "$$TRACE_EXECUTOR_SHA256  .cache/execution/SMT-COMP-2024-trace-executor.tar.gz" | sha256sum -c -

model-validator:
	@command -v docker >/dev/null || \
		{ echo "Docker with buildx is required by the official Dolmen build" >&2; exit 2; }
	@docker buildx version >/dev/null || \
		{ echo "docker buildx is required by the official Dolmen build" >&2; exit 2; }
	@if [[ ! -d .cache/official/external-tools/dolmen/docker/dolmen/.git ]]; then \
		source versions.env; git clone "$$DOLMEN_REPOSITORY" \
			.cache/official/external-tools/dolmen/docker/dolmen; \
	fi
	$(SMTCOMP) build-dolmen .cache/official/data

prepare:
	@test -n "$(CONFIG)" || { echo "unsupported TRACK=$(TRACK)" >&2; exit 2; }
	@test -n "$(SELECTION)" || { echo "missing selection mapping for TRACK=$(TRACK)" >&2; exit 2; }
	@if [[ "$(TRACK)" == "Incremental" && ! -x "$(TRACE_EXECUTOR)" ]]; then \
		$(MAKE) execution-tools; \
	fi
	$(PYTHON) -m smtcomp_harness.prepare \
		--track $(TRACK) --config $(CONFIG) --cvc5 $(CVC5) \
		--selection $(SELECTION) --output $(XML) $(DIVISION_ARG) \
		--performance $(PERFORMANCE) \
		$(if $(filter Incremental,$(TRACK)),--trace-executor $(TRACE_EXECUTOR),)

run: prepare
	$(PYTHON) -m benchexec.benchexec $(XML) -o $(RESULTS)
	@if [[ "$(TRACK)" == "ModelValidation" ]]; then \
		$(MAKE) validate-model RESULTS="$(RESULTS)"; \
	elif [[ "$(TRACK)" == "UnsatCore" ]]; then \
		$(MAKE) validate-unsat-core RESULTS="$(RESULTS)" DIVISION="$(DIVISION)"; \
	else \
		$(SMTCOMP) convert-benchexec-results "$(RESULTS)" --no-cache; \
	fi

validate-model: model-validator
	$(SMTCOMP) check-model-locally .cache/official/data .cache/execution "$(RESULTS)"
	$(SMTCOMP) convert-benchexec-results "$(RESULTS)" --no-cache

validate-unsat-core:
	$(MAKE) generate-unsat-core-validation RESULTS="$(RESULTS)" DIVISION="$(DIVISION)"
	@if [[ "$(UC_VALIDATION_MODE)" == "cvc5" ]]; then \
		$(MAKE) run-unsat-core-validator RESULTS="$(RESULTS)" DIVISION="$(DIVISION)"; \
		$(MAKE) merge-unsat-core-validation RESULTS="$(RESULTS)"; \
	elif [[ "$(UC_VALIDATION_MODE)" == "public-pool" ]]; then \
		$(MAKE) run-unsat-core-validator-pool RESULTS="$(RESULTS)" DIVISION="$(DIVISION)"; \
		$(MAKE) merge-unsat-core-validation RESULTS="$(RESULTS)"; \
	elif [[ "$(UC_VALIDATION_MODE)" == "external" ]]; then \
		echo "Validation tasks generated. Run the official validator pool into $(UC_VALIDATION_RESULTS)," >&2; \
		echo "then execute: make merge-unsat-core-validation TRACK=UnsatCore RUN_ID=$(RUN_ID)" >&2; \
		exit 2; \
	else \
		echo "UC_VALIDATION_MODE must be cvc5, public-pool, or external" >&2; exit 2; \
	fi

generate-unsat-core-validation:
	@test "$$(basename "$(RESULTS)")" = "results_unsatcore" || \
		{ echo "UnsatCore RESULTS must end in results_unsatcore for the official merger" >&2; exit 2; }
	@test -x .cache/scrambler/scrambler || \
		{ echo "Official scrambler is missing; install Flex/Bison and run make setup" >&2; exit 2; }
	$(SMTCOMP) generate-unsatcore-validation-files \
		.cache/execution .cache/scrambler/scrambler "$(RESULTS)"
	$(PYTHON) -m smtcomp_harness.prepare \
		--track UnsatCoreValidation --config configs/cvc5/SingleQuery/par.toml \
		--cvc5 .cache/solver/default/bin/cvc5 \
		--selection .cache/execution/benchmarks/files_unsatcorevalidation \
		--output work/cvc5-UnsatCoreValidation.xml $(DIVISION_ARG)

manifest-unsat-core-validator-pool: metadata
	$(PYTHON) -m smtcomp_harness.uc_validator_pool manifest \
		--data .cache/official/data --submissions .cache/official/submissions \
		--manifest $(UC_VALIDATOR_MANIFEST) $(DIVISION_ARG)

build-unsat-core-validator-pool: metadata execution-tools
	$(PYTHON) -m smtcomp_harness.uc_validator_pool build \
		--data .cache/official/data --submissions .cache/official/submissions \
		--cache $(UC_VALIDATOR_CACHE) --manifest $(UC_VALIDATOR_MANIFEST) $(DIVISION_ARG)

run-unsat-core-validator-pool: build-unsat-core-validator-pool
	$(PYTHON) -m smtcomp_harness.uc_validator_pool run \
		--cache $(UC_VALIDATOR_CACHE) --manifest $(UC_VALIDATOR_MANIFEST) \
		--results $(UC_VALIDATION_RESULTS)

run-unsat-core-validator:
	$(PYTHON) -m benchexec.benchexec work/cvc5-UnsatCoreValidation.xml -o $(UC_VALIDATION_RESULTS)

merge-unsat-core-validation:
	@test -n "$$(find "$(UC_VALIDATION_RESULTS)" -name '*.xml.bz2' -print -quit 2>/dev/null)" || \
		{ echo "No validator results in $(UC_VALIDATION_RESULTS)" >&2; exit 2; }
	cp .cache/execution/benchmarks/files_unsatcorevalidation/mapping.json $(UC_VALIDATION_RESULTS)/mapping.json
	$(SMTCOMP) convert-benchexec-results $(UC_VALIDATION_RESULTS) --no-cache
	$(SMTCOMP) convert-benchexec-results "$(RESULTS)" --no-cache

score:
	@test -n "$(TRACK)" || { echo "TRACK is required" >&2; exit 2; }
	@test -n "$(DIVISION)" || { echo "DIVISION is required; run 'make score-matrix'" >&2; exit 2; }
	@test -n "$(KIND)" || { echo "PERFORMANCE (or KIND) is required" >&2; exit 2; }
	$(PYTHON) -m smtcomp_harness.score --data .cache/official/data \
		--track $(TRACK) --kind $(KIND) $(DIVISION_ARG) $(RESULTS)

score-overall:
	$(PYTHON) -m smtcomp_harness.score --data .cache/official/data \
		--track $(TRACK) --overall --solver cvc5 $(RESULTS)

score-matrix:
	$(PYTHON) -m smtcomp_harness.matrix

# Compatibility aliases; both use the generic Track-aware implementation.
score-24:
	$(MAKE) score TRACK=SingleQuery KIND=24

score-parallel:
	$(MAKE) score TRACK=Parallel KIND=par

clean:
	find src tests scripts -type d -name __pycache__ -prune -exec find {} -depth -delete \;
