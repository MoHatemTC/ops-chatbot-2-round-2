# Product Requirements Document — AI Operations Support Agent

| | |
| --- | --- |
| **Product** | AI Operations Support Agent |
| **Status** | Draft |
| **Author** | Operations / Engineering |
| **Last updated** | 2026-07-09 |
| **Related docs** | [Project overview](project-overview.md) · [Delivery plan](plan/README.md) · [Architecture](architecture.md) |

## 1. Overview

The AI Operations Support Agent is a virtual assistant that acts as the first line of support for learners in our programs. It answers common questions from approved Operations materials, sends proactive reminders and nudges, and hands complex or unresolved issues to the Operations team with a short conversation summary.

It is built on the existing FastAPI + LangGraph foundation in this repository (PostgreSQL + pgvector, JWT auth, Langfuse observability, Prometheus/Grafana monitoring).

## 2. Problem statement

The Operations team spends a large share of its time on repetitive manual work:

- Answering the same learner questions many times
- Sending schedule and deadline reminders
- Following up on missing learner information
- Checking weekly learner progress
- Reading long chat histories before helping with an issue

This creates inbox clutter, slows response times, and limits how many learners the team can support. Learners, in turn, wait longer than necessary for answers that already exist in approved materials.

## 3. Goals

1. **Reduce repetitive work** — the assistant handles common questions and routine follow-ups automatically.
2. **Respond quickly** — learners get near-immediate answers about schedules, onboarding, curriculum, and deadlines.
3. **Support learners proactively** — timely reminders before sessions and deadlines, and supportive nudges for learners falling behind.
4. **Keep answers reliable** — the assistant answers **only** from approved Operations materials, and clearly says so when it does not know.
5. **Make future programs easier to launch** — onboarding a new cohort means updating schedules, FAQs, and materials, not rebuilding the system.

## 4. Non-goals

- Replacing human judgment — complex, sensitive, or ambiguous issues are always escalated to a person.
- Answering from general model knowledge — anything not covered by approved materials is out of scope for the assistant.
- Academic tutoring or grading — the assistant supports program operations, not curriculum content mastery.
- Building a full ticketing product — escalations integrate with the team's chosen ticketing workspace.

## 5. Users & personas

| Persona | Needs | What they get |
| --- | --- | --- |
| **Learner / intern** | Fast answers, timely reminders, help staying on track | 24/7 chat support, reminders, supportive nudges |
| **Operations team** | Less repetitive work, clear context when stepping in | Fewer routine messages, tickets with concise summaries |
| **Program lead** | Visibility into cohort health and support load | Dashboards for volume, escalations, at-risk trends |

## 6. User stories

### Learner

- As a learner, I can ask a question about schedules, onboarding, curriculum, or expectations and get an accurate answer within seconds.
- As a learner, if the assistant doesn't know the answer, it tells me honestly and hands my question to a human.
- As a learner, I receive a reminder before each session and before task/project deadlines.
- As a learner falling behind, I receive an encouraging, non-judgmental nudge.
- As a learner, I can control which notifications I receive and opt out.

### Operations team

- As an Ops member, I receive a ticket with a short structured summary (problem, what was tried, context, suggested next step) whenever an issue is escalated — I never have to read a full chat log first.
- As an Ops member, I can list, view, and resolve tickets, and see them in our ticketing workspace.
- As an Ops member, the assistant collects missing learner profile info in-chat so I don't have to chase it.

### Program lead

- As a program lead, I can see support volume, resolution times, and at-risk learner trends on a dashboard.
- As a program lead, I can launch the assistant for a new cohort by supplying materials and configuration only.

## 7. Functional requirements

Requirements are grouped by rollout phase; each maps to a sprint in the [delivery plan](plan/README.md).

### Phase 1 — Always-on assistant (Sprints 1–2)

| ID | Requirement | Priority |
| --- | --- | --- |
| F1.1 | Ingest approved materials (FAQs, onboarding notes, schedules, program docs) into a searchable knowledge base with source metadata | Must |
| F1.2 | Answer learner questions using retrieval over approved materials only, with source attribution | Must |
| F1.3 | Clearly admit when no grounded answer exists — never fabricate | Must |
| F1.4 | Detect escalation triggers (unknown answer, frustration, explicit request, repeated failures) | Must |
| F1.5 | Create a support ticket with a short structured conversation summary and notify Ops | Must |
| F1.6 | Provide authenticated APIs for Ops to list, view, and resolve tickets | Must |

### Phase 2 — Proactive coach (Sprint 3)

| ID | Requirement | Priority |
| --- | --- | --- |
| F2.1 | Send reminders before upcoming sessions (configurable lead time, deduplicated) | Must |
| F2.2 | Send reminders before task and project deadlines | Must |
| F2.3 | Detect learners at risk of falling behind (missed deadlines, inactivity, low progress, low feedback) | Must |
| F2.4 | Send encouraging nudges to at-risk learners, with frequency caps | Should |
| F2.5 | Follow up with learners who leave low feedback scores | Should |
| F2.6 | Let learners manage notification preferences and opt out | Must |

### Phase 3 — Ops command center (Sprint 4)

| ID | Requirement | Priority |
| --- | --- | --- |
| F3.1 | Ask learners for missing profile information during a chat and persist validated answers | Should |
| F3.2 | Send unresolved issues to the team's chosen ticketing workspace, with status sync | Must |
| F3.3 | Provide dashboards of open issues, support volume, and at-risk trends | Must |
| F3.4 | Support multiple cohorts via configuration and per-cohort materials, with no answer leakage between cohorts | Must |
| F3.5 | Deliver handoff documentation: admin guide, materials-update instructions, runbook | Must |

## 8. Non-functional requirements

| Category | Requirement |
| --- | --- |
| **Reliability of answers** | Responses must be grounded in approved materials; out-of-scope questions produce an honest refusal + escalation path |
| **Latency** | Chat responses stream; first token within a few seconds under normal load |
| **Availability** | Assistant available 24/7; scheduled jobs (reminders/nudges) are idempotent and retried with backoff (tenacity) |
| **Security** | JWT-authenticated sessions; all endpoints rate-limited; no secrets in code; learner data validated with Pydantic |
| **Privacy** | Escalation summaries include only necessary context; notifications respect learner opt-out |
| **Observability** | All LLM calls traced in Langfuse; Prometheus metrics for KPIs; structured logging with request/session/user context |
| **Quality assurance** | Grounding, correctness, and honest-refusal measured by the eval suite (`evals/`) with reported success rates |
| **Maintainability** | Follows the project's coding conventions; passes `make check` (lint + typecheck) |

## 9. Success metrics

| Metric | Target (initial) |
| --- | --- |
| Common questions answered without human help | ≥ 70% of support volume |
| Median first-response time for learner questions | < 10 seconds |
| Grounding/faithfulness eval success rate | ≥ 90% |
| Fabricated-answer rate on out-of-scope eval questions | ~0% (honest refusal instead) |
| Reminders delivered on time | ≥ 99% |
| Escalated tickets containing a usable summary | 100% |
| Ops time spent on repetitive requests | Measurably reduced vs. baseline (survey + volume metrics) |

Targets are initial estimates — revisit after Sprint 2 with real traffic.

## 10. Rollout & milestones

| Milestone | Scope | Delivery plan |
| --- | --- | --- |
| M1 — Grounded Q&A | Knowledge base + grounded answers + honest refusals + evals | [Sprint 1](plan/sprint-1/) |
| M2 — Phase 1 complete | Escalation, tickets, summaries, Ops APIs | [Sprint 2](plan/sprint-2/) |
| M3 — Phase 2 complete | Reminders, at-risk detection, nudges, preferences | [Sprint 3](plan/sprint-3/) |
| M4 — Phase 3 + handoff | Profile collection, ticketing integration, dashboards, cohort reuse, runbook | [Sprint 4](plan/sprint-4/) |

## 11. Assumptions & dependencies

- Approved source materials (FAQs, schedules, onboarding docs) are provided and kept current by Operations.
- Schedule and deadline data is available in a machine-readable form for reminders.
- The team selects a ticketing workspace for the Phase 3 integration.
- The existing platform services (PostgreSQL + pgvector, Langfuse, Prometheus/Grafana, LLM provider) remain available.

## 12. Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| Assistant hallucinates beyond approved materials | Retrieval-only answering, guardrail prompt, low-confidence fallback, grounding evals (F1.2–F1.3) |
| Over-messaging annoys learners | Frequency caps, preference controls, opt-out (F2.4, F2.6) |
| Escalations lost on connector failure | Internal tickets are the source of truth; connector retries; internal open-issues view (F3.2) |
| Stale source materials produce wrong answers | Re-runnable ingestion with update-not-duplicate semantics; admin guide for updating materials (F1.1, F3.5) |
| Cross-cohort answer leakage | Cohort-scoped knowledge and verification (F3.4) |

## 13. Open questions

- Which ticketing workspace will Ops standardize on for Phase 3?
- Which delivery channels (in-app only vs. email/other) are in scope for reminders at launch?
- What are the exact at-risk thresholds (missed deadlines, inactivity window) for the first cohort?
- Who owns curating and approving the source materials per cohort?
