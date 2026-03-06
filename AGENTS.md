# Desktop License Plate Recognition Application

The project uses several video channels. The number recognition on each channel works separately and independently from each other.

## Design Principles

- **SOLID** — separation of responsibilities between components
- **DRY** — no code duplication / Don’t Repeat Yourself
- **KISS** — simplicity of implementation and maintenance / Keep It Simple, Stupid
- **Multi‑layer architecture** — clear separation into UI, logic, data, and infrastructure layers
- **Design Patterns** — use established patterns to solve common problems, improve code maintainability, and facilitate communication among developers
- **Modularity** — the system should be composed of loosely coupled modules that can be independently developed, tested, replaced, or removed with minimal impact on the rest of the application

When adding or changing algorithms and functions, don't forget to add or update them in readme.md in Russian.

Make all Pull Requests in Russian.

Don't forget to update the project structure in readme.md.



## Mission

Migrate this repository from a desktop ANPR application to a web-first service architecture.

Primary objective:
- remove desktop UI as the product interface;
- preserve and reuse ANPR/CV/OCR/postprocessing core logic;
- preserve independent per-channel processing;
- move the system toward deployable backend + web UI services.

Do real implementation work. Do not stop at architectural discussion only.

---

## Non-negotiable rules

1. Do not move CV, OCR, inference, or video decoding into the browser.
2. Preserve the current principle: each video channel has an independent lifecycle and independent processing.
3. Do not delete working reusable core logic before it is migrated or replaced.
4. Do not remove desktop UI until web MVP is operational for critical workflows.
5. Prefer incremental migration over broad rewrites.
6. Keep changes runnable and verifiable.
7. When uncertain, preserve existing business behavior and refactor structure around it.

---

## Target architecture

The target system should evolve toward these services:

- **ANPR Core Service**
  - detection
  - OCR
  - postprocessing
  - per-channel lifecycle
  - channel control APIs

- **Video Gateway**
  - RTSP ingest
  - WebRTC for low-latency live preview
  - HLS for archive / mass viewing
  - multiple quality profiles

- **Event & Telemetry Service**
  - live ANPR events to UI via WebSocket or SSE
  - health checks
  - metrics
  - reconnect / timeout / error visibility

- **Web UI**
  - channel monitoring dashboard
  - live event feed
  - channel / ROI / lists / settings management

- **Data Layer**
  - event storage
  - optional media archive
  - retention / rotation / export

---

## Video handling rules

- Use **RTSP** for server-side ingest from cameras.
- Use **WebRTC** for operator live monitoring.
- Use **HLS** for archive playback or mass viewing.
- Do not stream maximum-quality raw video for all channels to the browser at once.
- Support 2–3 quality profiles where applicable.
- Reduce FPS / resolution for background or non-visible tiles.
- Keep decode and inference server-side.

---

## Migration priorities

Complete work in this order unless a strong repository-specific reason requires adjustment:

1. Audit current repository structure.
2. Identify reusable core vs desktop UI vs infrastructure code.
3. Build module mapping from current code to target services.
4. Extract ANPR Core Service.
5. Add event pipeline (WebSocket or SSE).
6. Build Web UI MVP.
7. Add Video Gateway capabilities.
8. Improve Data Layer and operations.
9. Remove desktop UI after web MVP is operational.

If the full migration is too large for one pass, reach this minimum milestone first:

**audit -> core extraction -> event pipeline -> web MVP**

---

## Required behavior for each task

For each meaningful phase or patch:

- explain what was found;
- explain what changed;
- list files created / moved / modified / deleted;
- list remaining risks or follow-up items.

When making a large change:
- inspect the existing structure first;
- reuse working modules when reasonable;
- update imports, entrypoints, and docs consistently;
- keep the repo buildable where possible.

---

## Definition of done for first working milestone

Do not call the migration “done” unless all of the following are true:

- project can run without desktop UI as the product entrypoint;
- ANPR backend/core service exists and runs;
- API exists for channels, ROI, and lists;
- live ANPR events can reach the web UI;
- a minimal web UI exists for monitoring and events;
- at least one channel can be created, started, stopped, and emit ANPR events;
- run instructions are updated.

---

## Repository expectations

When editing this repository:

- prefer clear service boundaries over UI-driven coupling;
- keep per-channel runtime logic isolated;
- avoid introducing browser-side inference logic;
- avoid hidden magic behavior;
- keep configuration explicit and documented;
- update README when commands, structure, or startup flow changes.

---

## Testing and verification

Before claiming completion of a feature:

1. run relevant tests if they exist;
2. run lint / type-check if configured;
3. validate startup commands for changed services if practical;
4. confirm imports and entrypoints are still correct;
5. mention anything you could not verify.

If tests are missing, add lightweight validation where reasonable.

---

## Implementation style

- Prefer small, reviewable commits/patches.
- Prefer migration by extraction over full rewrite.
- Preserve behavior first, optimize second.
- Keep naming consistent with the target service architecture.
- Document assumptions explicitly.

---

## Desktop deprecation policy

Desktop UI is deprecated and should be removed from the final product.

However:
- freeze or minimize desktop-specific changes unless needed for migration safety;
- do not delete desktop code prematurely if it is still needed as a temporary reference;
- once web MVP covers critical workflows, remove desktop UI code, dependencies, and obsolete build/runtime paths.

---

## Expected final repository direction

A good target shape is:

anpr-web/
- apps/web
- apps/api
- apps/worker
- packages/anpr-core
- infra/
- README.md

This is a direction, not a reason to rewrite everything blindly.
Prefer guided migration from current code into this shape.

