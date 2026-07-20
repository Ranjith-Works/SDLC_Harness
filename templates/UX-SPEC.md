# 04 — UX Specification

> Stage artifact. Filled by `/sdlc:design` from the User Stories. Feeds the TRD and `/sdlc:implement`.
> Validate with `/sdlc:gate` before advancing. Only produced for projects with a UI (STATE.md ui:true).

## Screens
<!--
Every screen/view, each traced to the user stories it serves (reference US-# ids). For each:
purpose, entry points, primary user actions, and the key layout. A wireframe (ascii/mermaid) helps.
-->

## Component Inventory
<!-- Reusable components (buttons, forms, tables, modals, ...) and where each is used. This is the
     source of truth the reviewer checks against for styling drift. -->

## States
<!--
For EVERY screen/component, define all states — not just the happy path:
  - loading (data in flight)
  - empty (no data yet)
  - error (request failed / invalid input)
  - success / populated
The ux review checklist verifies loading, empty, and error states are all handled.
-->

## Accessibility
<!--
Concrete a11y requirements: keyboard navigation, focus order, color contrast ratios (WCAG AA),
aria labels / alt text, screen-reader behavior. These are reviewed and (where tooled) scored via axe.
-->

## Responsive
<!-- Breakpoints and how the layout adapts (mobile / tablet / desktop). What must not break small. -->

## Design Tokens
<!-- Colors, type scale, spacing, radii — the shared vocabulary implementation must use. -->

## Visual / a11y Test Approach
<!-- How the UI is checked with tools: e.g. Playwright screenshots per screen+state, axe a11y scan,
     Lighthouse. Declare the command in eval.config.json under the `ux` slot so it scores. -->
