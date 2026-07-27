# Submission Checklist

## Challenge Integrity

- [ ] only `submission.py` contains challenge changes
- [ ] `git diff origin/main -- tests/ benchmarks/ cvc5_cloud/ aws-build/` is empty
- [ ] no benchmark-specific answers or expected-status lookup
- [ ] no generated files or local credentials are committed
- [ ] the cvc5 revision remains pinned

## Local Verification

- [ ] `make test`
- [ ] `make smoke`
- [ ] `make score`
- [ ] report solved, wrong, unknown, wall-time, and PAR-2 results

## Cloud Qualification

- [ ] `source scripts/activate_infrastructure.sh`
- [ ] `satcomp.py configs/local.yml --build`
- [ ] `satcomp.py ... --test-local`
- [ ] `satcomp.py configs/local.yml --acceptance-test`
- [ ] distributed local test with two worker containers
- [ ] container runs as `ecs-user`
- [ ] no runtime network dependency
- [ ] SAT/UNSAT/UNKNOWN map to exit codes 10/20/0
- [ ] timeout kills local and remote solver processes
- [ ] second benchmark on the same containers starts cleanly
- [ ] run a low-cost 1-leader/2-worker AWS qualification
- [ ] inspect stdout, stderr, process status, and timing artifacts
- [ ] terminate instances and verify that billed resources are gone

## External Competition

- [ ] identify a current competition with a compatible distributed track
- [ ] read that competition's current rules and submission instructions
- [ ] confirm portfolio or derived-solver eligibility
- [ ] name and document the entry as a cvc5-derived solver if required
- [ ] add authors and affiliations to the system description
- [ ] validate the exact commit submitted to the organizers
