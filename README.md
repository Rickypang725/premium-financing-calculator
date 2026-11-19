# Premium Financing Calculator

Clean-room rebuild of a premium-financing (保費融資) sales-advisory calculator, built as a cloud-engineering portfolio project. Domain: single-premium participating whole-life policies financed by bank loans, as sold to HK insurance advisors.

**Contract-first rebuild.** The initial state of this repository is the behavioural contract only: golden vectors reverse-verified against the reference tool's live UI (2026-11-09) plus the functional spec — implementation follows in milestone branches. See `docs/03-roadmap.md`.

## Why contract-first

An earlier rebuild implemented first and verified later, which left no objective anchor for correctness. This rebuild keeps the independently verified contract and regenerates everything else on top of it, so every number the engine produces is traceable to a third-party product's observed behaviour.

## Layout

- `tests/` — golden-vector contract (the executable spec; do not weaken)
- `docs/` — architecture, functional spec, roadmap with acceptance criteria per milestone

## Milestones

| # | Scope |
|---|---|
| M0 | Calculation engine (`src/pfpro/engine.py`) — stdlib only, pure functions |
| M1 | REST API (FastAPI) over the engine |
| M2a| Docker（multi-stage、非 root）|
| M2b| Terraform → AWS ECS Fargate（ADR-8，運行於 cloud-lab VPC）|
| M3| GitHub Actions CI/CD（OIDC → ECR → ECS）|
| M4 | React frontend (API-only, no embedded calculation) |

Milestone details and acceptance criteria: `docs/03-roadmap.md`.
