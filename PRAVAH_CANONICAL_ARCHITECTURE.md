# PRAVAH_CANONICAL_ARCHITECTURE

**Status:** Constitutional reference material

This document defines the canonical architecture of Pravah. It is the authority boundary for all Pravah implementations in this workspace and is intended to prevent role drift, schema drift, and hidden fallback behavior.

Primary evidence sources:
- [multi-agent-control-plane-main/README.md](multi-agent-control-plane-main/README.md)
- [multi-agent-control-plane-main/ARCHITECTURE_CURRENT.md](multi-agent-control-plane-main/ARCHITECTURE_CURRENT.md)
- [multi-agent-control-plane-main/RUNTIME_CONTRACT.md](multi-agent-control-plane-main/RUNTIME_CONTRACT.md)
- [PRAVAH_SYSTEM_DOSSIER.md](PRAVAH_SYSTEM_DOSSIER.md)
- [FULL_CONVERGENCE_MAP.md](FULL_CONVERGENCE_MAP.md)

---

## Canonical Role

Pravah is the canonical multi-agent control-plane platform for this workspace. Its role is to ingest runtime signals, validate them, decide on actions, enforce safety and governance rules, execute approved actions, observe outcomes, and expose an operator-facing dashboard.

Pravah also serves as the coordination layer between runtime monitoring, decisioning, execution, and operator visibility. The canonical runtime loop is the sense -> validate -> decide -> enforce -> act -> observe -> explain sequence described in [multi-agent-control-plane-main/README.md](multi-agent-control-plane-main/README.md).

---

## Upstream Dependencies

Pravah depends on the following upstream inputs and systems:

- Runtime payload producers that emit the canonical payload defined in [multi-agent-control-plane-main/RUNTIME_CONTRACT.md](multi-agent-control-plane-main/RUNTIME_CONTRACT.md).
- Control-plane runtime intake and governance logic in `control_plane/api/agent_api.py` and related runtime validation modules.
- Decision Brain logic exposed through the FastAPI backend in `control_plane/backend/app/main.py`.
- Optional observability signals from runtime pollers and runtime metrics files when present.
- App registry data from `control_plane/config/apps_registry.json`.
- Enforcement headers and trace propagation expectations from Sarathi and the control-plane execution path.

Dependency rule:
- Upstream systems may feed Pravah.
- Upstream systems may not redefine Pravah's canonical payload, execution gates, or authority model.

---

## Downstream Participants

Pravah serves the following downstream participants:

- Operator dashboard users through `dashboard/frontend`.
- Execution consumers that depend on approved actions from the control plane.
- Decision and lineage consumers that require runtime summaries, recent activity, and decision summaries.
- Integration consumers that read `/live-dashboard`, `/orchestration/metrics`, `/control-plane/status`, and related APIs.

Downstream rule:
- Participants may consume Pravah outputs.
- Participants may not mutate canonical runtime state unless they are explicitly part of the execution boundary.

---

## Execution Boundary

The execution boundary begins when a validated runtime payload enters Pravah and ends when an approved action is executed or refused.

Inside the execution boundary:
- Payload validation.
- Governance checks.
- Cooldown enforcement.
- Manual freeze enforcement.
- Decision generation.
- Execution admission and refusal semantics.

Outside the execution boundary:
- UI rendering.
- External telemetry collection.
- Independent replay analysis.
- Read-only dashboards and reports.

Boundary rule:
- Only canonical runtime intake may drive execution decisions.
- Dashboards must never be treated as execution authorities.

---

## Validation Boundary

Validation is a hard gate. The canonical runtime payload must validate against [multi-agent-control-plane-main/runtime_payload_schema.json](multi-agent-control-plane-main/runtime_payload_schema.json) before any execution path is allowed.

Validation boundary requirements:
- Required fields must be present.
- Extra fields are not permitted.
- Invalid payloads must be refused, not coerced.
- Schema discipline takes precedence over convenience.

Validation modules referenced in the repo:
- `control_plane/core/input_validator.py`
- `control_plane/core/runtime_event_validator.py`

Validation rule:
- If a payload cannot be validated, Pravah must reject it and disclose the refusal explicitly.

---

## Authority Declaration

Pravah IS:
- The canonical control-plane authority for runtime intake, decisioning, governance, and operator-facing status.
- The owner of runtime payload validation and the runtime-to-decision execution path.
- The consumer and summarizer of approved upstream telemetry.
- The authority for safe action admission and refusal semantics.

Pravah IS NOT:
- The canonical observability stream transport.
- The canonical enforcement engine for Sarathi-style policy approval.
- The canonical source of truth for raw infrastructure telemetry if a specialized observability system exists upstream.
- A free-form dashboard that may invent or reshape runtime truth.

Authority rule:
- If a component changes runtime action eligibility, it belongs in the execution boundary.
- If a component only observes or visualizes, it does not gain authority over runtime state.

---

## Non-Authority Declaration

Pravah does not own the following unless explicitly delegated by a canonical upstream service:

- Raw service telemetry collection.
- Trace store replay semantics.
- Observability transport internals.
- External caller identity trust beyond enforced request headers and schema checks.
- Synthetic metric fabrication.

Non-authority rule:
- Visualization data is not operational truth unless it can be traced to a validated upstream source.
- Demo values, hash-based metrics, or fallback placeholders are not canonical.

---

## Replay Boundary

Replay is read-only and must never alter live runtime state.

Canonical replay scope:
- Decision history.
- Execution lineage.
- Runtime snapshots.
- Operator audit trails.

Replay exclusions:
- Live execution gates.
- Manual freeze state changes.
- Governance decisions for the active runtime cycle.
- Any write path that could affect future decisioning.

Replay rule:
- Replay may explain what happened.
- Replay may not decide what happens next.

---

## Observability Boundary

Pravah may consume observability data and present it, but it must not redefine observability semantics.

Observability in Pravah includes:
- Runtime health summaries.
- Dashboard metrics.
- Decision summaries.
- Recent activity views.
- File status and deployment readiness indicators.

Observability outside Pravah's authority:
- Packet-level tracing internals.
- Trace queue semantics.
- Durable event transport guarantees.
- Stream isolation proofs.

Observability rule:
- Pravah may aggregate observability data into operator views.
- Pravah may not claim transport-level guarantees it does not implement.

---

## Enforcement Interaction

Pravah interacts with enforcement as a consumer and orchestrator, not as the enforcement authority itself.

Required enforcement behaviors:
- Honor `X-CALLER` and `X-TRACE-ID` style provenance when present.
- Refuse bypass attempts.
- Preserve decision and execution lineage where supported.
- Route approved actions through governed executors.

Interaction rule:
- Enforcement systems may block Pravah actions.
- Pravah may not bypass an enforcement system by inventing local authority.

---

## Schema Discipline

The canonical schema for runtime intake is frozen in [multi-agent-control-plane-main/runtime_payload_schema.json](multi-agent-control-plane-main/runtime_payload_schema.json).

Schema discipline requirements:
- Do not add fields silently.
- Do not infer missing fields.
- Do not reshape required field types.
- Do not replace the canonical payload with ad hoc dashboard objects.

Schema hierarchy:
1. Canonical runtime payload schema.
2. Internal enrichment only after validation.
3. Dashboard view models derived from canonical data.

Schema rule:
- View models are not contracts.
- Contracts are not suggestions.

---

## Hidden-State Disclosure

Any hidden state that can affect Pravah output must be disclosed.

Hidden-state examples:
- In-memory decision buffers.
- Fallback demo values.
- Hash-based synthetic metrics.
- Background loop status.
- Integration bridge availability.

Disclosure rule:
- If output depends on hidden state, the UI or API must mark that output as derived, partial, demo, unavailable, or fallback.
- Silent fallback is prohibited.

Pravah must explicitly disclose:
- Whether a value is live, derived, cached, demo, or unavailable.
- Whether a subsystem is connected or disconnected.
- Whether a metric is real, computed, or placeholder.

---

## Deployment Model

Pravah deploys as a three-service local topology in the current repo:

1. Flask Control Plane API on port 7000.
2. FastAPI Decision Brain API on port 8000.
3. Next.js frontend on port 4500.

Deployment rules:
- Local development may use separate processes.
- Production deployment must preserve the same authority boundaries.
- Runtime intake, decisioning, and dashboard rendering must remain separately identifiable.
- Deployment shortcuts may not collapse validation, decision, and display into one opaque service.

Deployment rule:
- A deployment may change packaging.
- A deployment may not change constitutional authority.

---

## Anti-Drift Protections

To prevent architecture drift, the following protections are mandatory:

- Canonical schema freeze for runtime payloads.
- Explicit authority declarations for each subsystem.
- Read-only replay boundaries.
- No silent fallback for missing telemetry or disconnected integrations.
- No synthetic metrics in production pathways unless explicitly marked demo.
- Single source of truth for runtime contracts.
- Versioned documentation for runtime, execution, and observability roles.
- Cross-check dashboard fields against backend endpoints before release.
- Require explicit disclosure when a value is derived or placeholder.

Anti-drift rule:
- If a new component changes runtime meaning, replay meaning, or observability meaning, it must be reconciled against this document before it becomes canonical.

---

## Constitutional Summary

Pravah IS:
- The canonical multi-agent control-plane authority for runtime validation, decisioning, governance, execution, and operator visibility.

Pravah IS NOT:
- The observability transport itself.
- The Sarathi enforcement authority.
- A place where hidden or synthetic state can masquerade as operational truth.

This document is the constitutional reference material for Pravah architecture decisions in this workspace.