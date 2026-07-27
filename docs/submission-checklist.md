# Submission Checklist

## Proven Locally

- [x] `make test`
- [x] `make smoke`
- [x] cvc5 revision in `versions.env` matches `aws-build/Dockerfile`
- [x] sequential, portfolio, and seeded-race outputs agree with expected
      smoke results
- [x] local and cloud YAML pass the pinned harness `ProjectConfig` parser
- [x] `solver_cmd.py` passes the pinned harness I/O types

## Official Harness

- [ ] `satcomp.py configs/local.yml --build`
- [ ] `satcomp.py ... --test-local`
- [ ] `satcomp.py configs/local.yml --acceptance-test`
- [ ] distributed local test with two worker containers
- [ ] container runs as `ecs-user`
- [ ] no runtime network dependency
- [ ] SAT/UNSAT/UNKNOWN map to exit codes 10/20/0
- [ ] timeout kills local and remote solver processes
- [ ] second benchmark on the same containers starts cleanly

## AWS Qualification

- [ ] confirm the final instance type and worker count with organizers
- [ ] run a low-cost 1-leader/2-worker AWS qualification
- [ ] inspect S3 stdout, stderr, process status, and timing artifacts
- [ ] run the intended 99-worker configuration on representative hard inputs
- [ ] terminate instances and verify that billed resources are gone

## Submission

- [ ] confirm that a same-solver seeded race/internal portfolio is eligible
- [ ] name and document the entry as a cvc5-derived solver if required
- [ ] keep this repository and all fetched build sources public
- [ ] add authors and affiliations to the system description
- [ ] submit the repository containing top-level `aws-build/`
- [ ] preliminary submission by August 8, 2026
- [ ] final submission by August 22, 2026, 11:59 PM AoE
