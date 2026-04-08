# Operator Console — UI Design System

Purpose: Define visual style, layout, and interaction patterns for **operator-console** as an **internal** product surface over **api-gateway**. This document is normative for console implementation choices that affect clarity, consistency, and alignment with platform semantics.

**Scope:** Presentation and interaction only. Execution lifecycle, policy, validation, persistence, and metrics computation remain owned by platform services and published contracts ([project-constitution.md](../overview/project-constitution.md) §2.4, §8.8–8.10; [project-end-state.md](../overview/project-end-state.md) §2.7, Phase 8).

---

## 1. Design Philosophy

- **Minimal interface:** Only elements that support operator tasks (explore executions, inspect trace, act on approvals, submit feedback, read evaluation and advisory insights as APIs expose them). Omit ornament, redundant chrome, and decorative imagery.
- **Information-first:** Primary content is **data about executions**—identifiers, states, timestamps, classifications, and links to persisted records—not narrative marketing or empty states framed as product storytelling.
- **No decorative UI:** No non-functional gradients, illustrations, or visual motifs whose removal would not reduce operator capability.
- **Clarity over visual richness:** Prefer legible tables, consistent labels, and explicit empty and error states over dense styling or ambiguous icon-only affordances for critical actions.
- **Precision and control-panel feel:** Layout and density should read as **operational tooling**: aligned grids, predictable regions (list → detail → trace), and explicit affordances for sort, filter, expand, and submit—analogous to internal dashboards and incident tools, not consumer applications.

**Constitutional alignment:** The console is a **thin** consumer of **api-gateway**; it **must not** redefine execution semantics or host authoritative state ([project-constitution.md](../overview/project-constitution.md) §8.8–8.9). Presentation follows **platform vocabulary** (execution, plan, step, tool call, policy evaluation, approval, validation, timeline) as in [runtime-model.md](../architecture/runtime-model.md) and [api-design.md](../architecture/api-design.md).

**Note on document numbering:** [project-constitution.md](../overview/project-constitution.md) defines sections through **§11** (implementation enforcement); there is **no §12** in the current file. This UI system aligns with **§8** (implementation and product surface rules), **§11.8–11.9** (product surface and metrics/insights enforcement), and **Phase 8** in [project-end-state.md](../overview/project-end-state.md). Typography and visual discipline here support **§8.7–8.8** (clarity, thin product surface) and **§11.8** (no embedded core logic in UI).

---

## 2. Color System

**Default theme:** **Dark-first** — reduces eye strain for long trace review sessions and matches common internal ops tooling conventions.

| Role | Intent |
|------|--------|
| **Background** | Near-black or deep gray; single base layer for the application frame. |
| **Surfaces** | Slightly lighter elevated layers for panels, cards, and tables (clear step from background). |
| **Primary text** | High-contrast neutral (e.g. near-white) for identifiers, titles, and primary data. |
| **Secondary text** | Muted gray for metadata, hints, column headers, and de-emphasized fields. |
| **Border / divider** | Low-contrast line or hairline; sufficient for grouping without visual noise. |
| **Accent** | **One** controlled accent (e.g. blue or teal) reserved for **focus**, **primary actions**, **links**, and **selected** list rows—not for arbitrary decoration. |
| **Error** | Red (or red-adjacent) for failures, destructive emphasis, and validation errors. |
| **Warning** | Amber for caution, timeouts-at-risk, or attention without hard failure. |
| **Success** | Green for completed success paths and positive terminal states where the platform records success. |

**Rules**

- **No rainbow usage:** Do not assign multiple saturated hues to categories unless those categories are **fixed semantic enums** (e.g. status) and documented in this system.
- **Color only for meaning:** Use hue primarily for **state**, **status**, and **severity**. Neutral surfaces and typography carry structure; color signals outcome or attention.

**Metrics and insights:** Evaluation and Mukti views use the same palette; **anomaly** or **degradation** indicators map to **warning** / **error** semantics or neutral emphasis plus **numeric/text labels**—never undocumented “traffic light” logic that contradicts API-exposed definitions ([project-constitution.md](../overview/project-constitution.md) §4.4, §8.10).

---

## 3. Typography

### Font family

- **Primary font:** **Inter** — required for all **operator-console** UI text (navigation, tables, forms, buttons, headings, labels, and prose).
- **Inter must be used across all UI surfaces** for proportional text. Load Inter via the project’s standard web font path (e.g. self-hosted or approved package); do not substitute **system UI**, **Arial**, or other sans families for body or headings.
- **No alternative primary fonts** are allowed unless **explicitly justified** in writing (e.g. legal or platform constraint) and the exception is recorded in the same change that introduces it; default remains Inter for all new work.

**Constitutional alignment:** A single enforced typeface supports **consistent, inspectable** operator views and avoids UI-led reinterpretation of platform data ([project-constitution.md](../overview/project-constitution.md) §8.7–8.9). There is **no §12** in the current constitution; alignment is with **§8** and **§11.8** as above.

### Typography principles

- Typography must be **clean**, **highly readable**, and **consistent across views** (list, detail, trace, approvals, feedback, evaluation/Mukti).
- **Avoid stylistic variation** that reduces clarity (mixed families, ad hoc letter-spacing, or display treatments on operational data).

### Scale and hierarchy

Define and **reuse** one scale across the app. Each level maps to **named tokens** or **shared styles** in implementation (no one-off pixel sizes per component).

| Level | Use |
|-------|-----|
| **Title** | Execution detail title, primary screen title (e.g. execution identifier context). |
| **Section headers** | Summary, Steps, Trace, Policy, Tools, Approvals, and other grouped blocks. |
| **Labels** | Field names, table headers, filter names, form labels. |
| **Data** | Values from APIs; primary table cell content. |
| **Secondary / meta** | Timestamps, secondary identifiers, hints, column sublabels. |

**Rules**

- **Font sizes must follow the defined scale** — document the numeric steps in implementation (e.g. design tokens); **do not arbitrarily change font sizes between components** for the same semantic level.
- **Avoid excessive size variation** — keep the number of distinct sizes **small** (typically one size per hierarchy row above, plus optional compact variant for dense tables if needed).

### Font usage rules

- **No bold overuse** — default body and data at regular weight; use **semibold or bold only for emphasis** (titles, active row, critical labels) where the scale defines it.
- **Avoid italic** unless **semantically required** (e.g. citations, quoted fragments in trace); do not use italic for decoration or hierarchy.
- **Numeric values** (IDs, timestamps, durations, metrics) must remain **highly readable**: prefer **tabular figures** where Inter supports them; align numbers in tables; do not shrink meta numerics below the documented minimum for **secondary / meta** text.
- **Monospace** is allowed **only** for:
  - **IDs** (when shown in isolation or code-style blocks),
  - **Raw JSON** and structured payloads,
  - **Trace payloads** and similar fixed-width-friendly content.  
  Use **one** neutral monospace stack for these cases only (e.g. `ui-monospace, SFMono-Regular, Menlo, monospace`); **do not** use monospace for general UI labels or titles. All other text uses **Inter**.

### Readability requirements

- Maintain **sufficient contrast** between text and background per §2 (primary text high-contrast; secondary text muted but **legible**).
- **Avoid low-contrast gray-on-gray** combinations that fail WCAG-style contrast for normal or small text; secondary text must remain scannable for IDs and timestamps.
- **Primary data** (titles, data cells, main labels) must be readable **without strain** at default zoom on target displays.

**Status and color:** Do not rely on color alone for status (pair with icon, label, or text) — unchanged from §7.

---

## 4. Layout Principles

- **Grid-based layout:** Page structure uses a consistent column grid; tables and forms align to the same vertical rhythm.
- **Consistent spacing:** Use a **spacing scale** (e.g. 4/8/12/16 px steps). Related controls share tighter spacing; sections are separated by larger steps.
- **Clear grouping:** Related fields and trace events are wrapped in **sections** or **panels** with explicit headings.

**Rules**

- **Avoid clutter:** Default views show **summaries**; secondary detail is collapsed, tabbed, or navigated—not stacked in one scroll of unrelated blocks.
- **Whitespace intentionally:** Use padding and grouping to separate **list**, **detail summary**, and **deep trace**—not arbitrary empty regions.
- **Strict alignment:** Form labels, table columns, and timeline markers align to grid lines; avoid ragged decorative layouts.

**Phase 8 alignment:** Execution explorer, execution detail, timeline/steps/tools/policy, approvals, and evaluation/Mukti insight surfaces should **reuse** the same layout primitives so operators learn one spatial model ([project-end-state.md](../overview/project-end-state.md) Phase 8).

---

## 5. Components

### 5.1 Execution List

- **Format:** **Tabular** or **dense list** with columns aligned to API fields (e.g. id, workflow, state, started/updated, initiator if exposed).
- **Behavior:** **Sortable** and **filterable** within **gateway-supported** query parameters; UI does not invent filters the API cannot satisfy.
- **Empty / loading:** Explicit states; no fake rows.

### 5.2 Execution Detail

- **Structure:** **Structured sections** (Summary, Steps, Tools, Policy, Approvals, Validation, Evidence, Timeline—**as data exists** for that execution).
- **Summary at top:** Identifiers, current execution state, workflow type, key timestamps, and short human-readable summary fields from API projections.
- **Deeper data below:** Steps, events, and payloads in scrollable or secondary panels; link to replay or related execution ids when API provides them.

### 5.3 Timeline / Trace

- **Format:** **Vertical timeline** or **grouped chronological list** (by step or correlation id as API models).
- **Separation:** Each event has clear **boundaries** (row, card, or rule-separated block) with timestamp, type, and state.
- **Expandable details:** Payloads, tool I/O, policy reasons, and approval records load or expand **on demand** to preserve scanability.

### 5.4 Step Card

- **Required elements:** **Step name** (or type), **status**, **duration** (or start/end if provided).
- **Expandable payload:** Step result, errors, evidence pointers, model path indicators—**as returned by APIs**—in collapsed-by-default regions or drawers.

### 5.5 Approval Panel

- **Decision state:** Show **pending / approved / rejected** (or API-equivalent) **explicitly** with timestamp and actor when persisted fields exist.
- **Actions:** **Explicit** primary buttons (e.g. Approve, Reject) wired to **real approval endpoints**; disabled or hidden when the execution is not in a gating state. No placeholder actions.

**Feedback submission** (where in scope): Same discipline—structured form fields tied to **feedback-service** contracts, not free-form “notes” that bypass schema.

---

## 6. Motion and Interaction

- **Minimal animation:** No ambient motion, parallax, or decorative loaders unrelated to data fetch.
- **Transitions only where they clarify:**
  - **Expand / collapse** for sections, step payloads, and timeline rows (short height/opacity transition acceptable).
  - **State changes** after actions (e.g. approval submitted → pending → confirmed from server response).

**Rules**

- **No decorative animations** (bouncing icons, celebratory effects).
- **No distracting movement** that draws attention away from status and data during triage.

---

## 7. Status Representation

Use **consistent** visuals across **list**, **detail**, **step cards**, and **timeline** for platform-reported states.

| Semantic | Visual direction |
|----------|------------------|
| **Running** | Accent or neutral pulse/subtle indicator + label “Running”; optional spinner only on live-updating regions. |
| **Completed** | Success semantic (green) + label; terminal success only if platform records validation success per constitution. |
| **Failed** | Error semantic (red) + label; pair with **failure class** text when API provides it ([project-constitution.md](../overview/project-constitution.md) §4.2). |
| **Awaiting approval** | Distinct pattern (e.g. warning accent border or amber icon) + label “Awaiting approval”; action panel visible. |

**Rules**

- **Visible at a glance:** Status appears in **list** and **detail** header without opening nested panels.
- **Consistent across screens:** Same color, iconography, and labels for the same enum values everywhere.

---

## 8. Data Density

- **Summaries by default:** List and detail **headers** show high-signal fields; large JSON and long text are truncated or collapsed.
- **Drill-down:** Expand rows, “View raw,” or secondary routes for full payloads, full trace, and comparison views (e.g. replay diff when Phase 8 exposes it).

**Rules**

- **Avoid overwhelming initial view:** Do not render full execution graphs as an unreadable wall of JSON on first paint.
- **Allow deep inspection:** Every persisted artifact the gateway exposes should be reachable within **few deliberate clicks** from the execution detail context.

**Evaluation / Mukti surfaces:** Present **aggregates and ranked lists** with **links** back to underlying executions or trace artifacts; treat advisory text as **inspectable** but **non-authoritative** for control ([project-constitution.md](../overview/project-constitution.md) §6.4, §11.9).

---

## 9. Interaction Rules

- **Actions map to real APIs:** Every button, form submit, and refresh triggers a **documented** gateway operation (executions, trace, approvals, feedback, metrics reads, replay where available). No client-only simulations of approve, cancel, or “re-run” unless backed by the same contracts as CLI or server paths.
- **No simulated actions:** Do not show success toasts for state that the server has not confirmed.
- **Immediate feedback:** After an action, show **pending** UI, then **success or error** from the **response**; **reconcile** list and detail with **server truth** ([project-constitution.md](../overview/project-constitution.md) §8.9).

**Optimistic UI:** If used for minor UX only, it must **reconcile** on error and must never override **execution state** display with stale client assumptions.

---

## 10. Non-Goals

The operator-console **must not** pursue:

- **Consumer UI patterns:** Marketing landing layouts, onboarding carousels, or brand-heavy empty states.
- **Gamification:** Points, streaks, badges, or competitive framing of operator work.
- **Chat-based UI:** Conversational shells as the **primary** execution or triage primitive ([project-constitution.md](../overview/project-constitution.md) §1; [project-end-state.md](../overview/project-end-state.md) §1).
- **Dashboard clutter:** Large widget grids of unrelated KPIs without trace attribution; **metrics** belong in views that **tie to** workflow, step, tool, policy dimensions as defined in [project-end-state.md](../overview/project-end-state.md) §2.8.

**Phase 8 explicit non-goals** for the product layer include **full-scale UI polish and accessibility programs** as completion blockers ([project-end-state.md](../overview/project-end-state.md) Phase 8 “May remain stubbed”). This design system defines **discipline and semantics**, not a full visual identity program or component library implementation.

---

## Document control

- **Related:** [project-constitution.md](../overview/project-constitution.md), [project-end-state.md](../overview/project-end-state.md), [api-design.md](../architecture/api-design.md), [runtime-model.md](../architecture/runtime-model.md).
- **Changes:** Updates here should remain consistent with gateway capabilities and shared schemas; if the API adds fields or states, extend **§5** and **§7** explicitly.
