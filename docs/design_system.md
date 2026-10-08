# Sherlog — Frontend Visual Design System

## 1. Product Tone & Design Philosophy

Sherlog is an AI-powered Incident Investigation & Response Platform.
The frontend represents a high-density, serious operational console for Site Reliability Engineers (SREs), Platform Engineers, and AI Infrastructure operators.

### Visual Character
- **Inspirations**: Linear, Vercel, Datadog, modern enterprise developer infrastructure.
- **Design Philosophy**: "Case File" — flat, disciplined, restrained, dark-first, and highly structured.
- **Anti-Patterns (STRICTLY PROHIBITED)**:
  - ❌ No generic SaaS or AI startup templates
  - ❌ No cyberpunk, hacker, neon, or glowing UI elements
  - ❌ No purple/blue AI dashboards
  - ❌ No excessive glassmorphism or background blur
  - ❌ No multi-stop gradients
  - ❌ No fake "AI thinking" shimmer/orb animations
  - ❌ No decorative robot/brain illustrations that convey no real information

---

## 2. Color Palette ("Case File")

All visual components must use the exact Sherlog "Case File" palette. Do not introduce arbitrary colors or deviate from these tokens.

| Role | Name | HEX Code | Tailwind Token | Semantic Usage |
| :--- | :--- | :--- | :--- | :--- |
| **Canvas Background** | **Ink** | `#14110F` | `ink` | Root app background, main canvas |
| **Card / Surface** | **Soot** | `#1D1915` | `soot` | Card containers, panels, modals, dropdowns |
| **Borders / Lines** | **Ash** | `#332D26` | `ash` | 1px dividers, card outlines, table gridlines |
| **Primary Text** | **Bone** | `#E8E1D2` | `bone` | Primary headings, titles, active nav labels, key values |
| **Secondary Text** | **Dust** | `#8C8576` | `dust` | Muted labels, timestamps, subtitles, inactive nav |
| **Investigation Activity** | **Amber** | `#E0A63A` | `amber-sherlog` | Evidence badges, investigation activity, warnings |
| **Incident / Alert** | **Vermilion** | `#E4572E` | `vermilion` | Critical alerts, active incidents, errors |
| **Verified / Success** | **Verdigris** | `#4FA38B` | `verdigris` | Verified root causes, resolved state, approved actions |
| **Untested Hypothesis** | **Slate** | `#8FA3C7` | `slate-sherlog` | Unverified hypotheses, neutral metrics, pending state |
| **Contradicted Evidence** | **Oxblood** | `#8E2F3C` | `oxblood` | Contradicted evidence, failed checks, reject button |

### Semantic Color Rules
- **Vermilion** = Critical alert, active incident trigger, active verification step.
- **Amber** = Evidence item, tool activity in progress, metric delta warning.
- **Slate** = Unverified hypothesis, neutral baseline metric, pending step.
- **Oxblood** = Contradicted hypothesis, invalidated evidence, reject action.
- **Verdigris** = Deterministically verified root cause, resolved incident, approved remediation.
- **Bone & Dust** = Primary and secondary UI typography.
- **Ash** = Structural 1px separation.
- **Accent Restraint**: Accent colors must be applied sparingly. More than 85% of the visible surface should remain `Ink`, `Soot`, `Bone`, and `Dust`.

---

## 3. Typography

### Font Stacks
- **UI & Headings**: Inter, Space Grotesk, or Inter Tight
  - Clean, neutral geometric sans-serif
  - Tight letter-spacing for headings (`tracking-tight`)
- **Code, Metrics & Telemetry**: JetBrains Mono or IBM Plex Mono
  - Used for PromQL queries, log excerpts, Git SHAs, timestamps, tool calls, and JSON diffs

### Hierarchy Scale
| Level | Font Family | Size | Weight | Color | Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Display / Page Title** | Sans-serif | `1.5rem` (24px) | Semibold (600) | `Bone` | "Good evening, Aarav", Incident Name |
| **Section Header** | Sans-serif | `1.125rem` (18px) | Medium (500) | `Bone` | Card titles ("Active Incidents", "System Health") |
| **Subheadings / Group** | Sans-serif | `0.875rem` (14px) | Medium (500) | `Bone` | "Top Hypotheses", "Live Agent Activity" |
| **Body Text** | Sans-serif | `0.875rem` (14px) | Normal (400) | `Bone` / `Dust` | Descriptions, incident notes |
| **Meta / Timestamps** | Sans / Mono | `0.75rem` (12px) | Normal (400) | `Dust` | Timestamps ("19:42:08"), breadcrumbs, sub-labels |
| **Code / Tool Call** | Monospace | `0.8125rem` (13px)| Normal (400) | `Bone` / `Amber` | `query_metrics(service='orders')` |

---

## 4. Visual Layout & Spatial Rules

- **Dark-First Surfaces**: No light mode; dark palette built on `#14110F` (Ink) and `#1D1915` (Soot).
- **Flat Elevation**: No dropshadow elevations (`shadow-none` or subtle `shadow-sm`). Depth is expressed purely through surface contrast (`Ink` vs `Soot`) and 1px `Ash` borders.
- **Borders**: All cards, modals, table rows, and panel dividers use a crisp `1px solid #332D26` (`border-ash`).
- **Restrained Radii**: Cards and containers use `rounded-md` (6px) or `rounded-lg` (8px). Badges and pill tags use `rounded-full`.
- **Information Density**: Compact padding (`p-3`, `p-4`, `p-5`) to maximize viewable telemetry without clutter.

---

## 5. Component Anatomy (Extracted from Reference Image)

### 1. Global Shell & Navigation
- **Docked Sidebar (Left)**:
  - Width: `w-60` (240px)
  - Logo: `SHERLOG` in bold Bone uppercase with `AI INCIDENT INVESTIGATION` subtext in Dust.
  - Nav Items: Overview, Incidents (with badge counter in Vermilion), Services, Knowledge, Evaluations, Audit Logs, Settings.
  - Active Nav Item: Flat Soot background (`bg-soot`), 1px border, text Bone (`text-bone`).
- **Top Header Bar**:
  - Global Search: `Search incidents, services, logs...` with `⌘ K` keyboard shortcut pill.
  - Operational Status: `● System Operational` with Verdigris indicator dot.
  - User Pill: Avatar initials (`AS`), user full name (`Aarav Sharma`), role (`admin`).

### 2. Overview KPI Cards (4-Column Grid)
- **Active Incidents**: Count (`3`), label, alert icon in Vermilion (`#E4572E`).
- **Services Monitored**: Count (`4`), label, stack/database icon in Bone.
- **Overall Uptime**: Percentage (`99.8%`), label, heartbeat icon in Verdigris (`#4FA38B`).
- **Investigations (24h)**: Count (`12`), label, casefile/document icon in Dust.

### 3. Triage & System Health Cards
- **Active Incidents List**:
  - Displays ID (`INC-00241`), title (`API latency spike`), target service (`Orders service`), status pill (`INVESTIGATING`), elapsed time (`5 min ago`).
- **System Health Overview**:
  - Per-service uptime (API: 99.9%, Orders: 98.7%, Payments: 99.4%, Auth: 99.8%).
  - Horizontal progress bars and micro-sparklines in Verdigris.
- **Service Metrics Graph**:
  - Tab toggles (`Latency`, `Error Rate`, `Throughput`), time range selector (`Last 1 hour`).
  - Multi-line SVG chart with discrete service color legend.

### 4. Active Incident Canvas (Drilldown View)
- **Incident Header**:
  - Breadcrumb / Back button (`← INC-00241`), status badge (`INVESTIGATING`), opened time.
  - Primary title (`API latency spike`), subtitle (`Orders service • High API latency...`).
  - Action buttons: `Share`, `Add Note`, `...`
- **Investigation Progress Stepper (Left Column)**:
  - Vertical timeline with connected step nodes:
    - Step 1: Alert received (`19:42:03`) — completed (Verdigris checkmark)
    - Step 2: Analyzing metrics (`19:42:04`) — completed (Verdigris checkmark)
    - Step 3: Searching logs (`19:42:05`) — completed (Verdigris checkmark)
    - Step 4: Checking deployments (`19:42:07`) — completed (Verdigris checkmark)
    - Step 5: Verifying hypothesis (`In progress...`) — active (Vermilion/Amber node)
    - Step 6: Generating conclusion (`Pending`) — upcoming (Slate outline node)
- **Investigation Tabs & Competing Hypotheses (Center Column)**:
  - Navigation tabs: `[Hypotheses] [Evidence] [Logs] [Metrics] [Traces] [Agent Activity]`
  - Ranked Hypotheses list:
    - Hypothesis 1: `Database connection pool exhaustion` — Score bar 82% — Badge: `LIKELY` (Verdigris)
    - Hypothesis 2: `Traffic spike` — Score bar 41% — Badge: `POSSIBLE` (Slate)
    - Hypothesis 3: `Payment service dependency` — Score bar 18% — Badge: `LESS LIKELY` (Oxblood / Slate)
  - Evidence Summary Cards:
    - `DB Connections`: 100% utilization (`+340% vs normal`) — Amber icon
    - `API Latency`: 1.2s (p95) (`+820% vs normal`) — Amber icon
    - `No Recent Deployments`: Last deployment 2 hours ago — Ash icon
- **Live Agent Activity Stream**:
  - Real-time terminal feed of agent state transitions and tool executions.
  - Timestamp in Dust, tool signature in Bone/Amber (e.g. `query_metrics(service='orders')`).
  - Output summary in Dust (e.g. `API latency increased 8.2x`).
- **Operational Knowledge & RAG Panel**:
  - Search input for operational documentation.
  - Category tabs: `[Runbooks] [Past Incidents] [Architecture] [FAQs]`.
  - Item listing: Title, step count, last updated timestamp.
- **Evaluation Benchmark Card**:
  - Top-1 Accuracy: `87.3% (↑ 6.2%)`.
  - Avg Steps: `2.4 (↓ 12%)`.
  - Avg Latency: `18.6s (↓ 28%)`.
  - Trendline sparkline across dates.
- **Remediation & Human Approval Dock (Bottom Panel)**:
  - **Proposed Root Cause** (Left):
    - Verified root cause summary in Verdigris.
    - Clear narrative of evidence correlation.
  - **Proposed Remediation** (Right):
    - Action title: `Increase database connection pool size`
    - Action detail: `Increase the connection pool from 20 to 40 connections.`
    - Configuration Diff link: `</> View Configuration Diff`
    - Mandatory Human-in-the-Loop Action Buttons:
      - `[✓ Approve]`: Solid Verdigris (`#4FA38B`) with dark text (`#14110F`), high contrast.
      - `[✕ Reject]`: Ash border button with Oxblood text/accent.

---

## 6. Tailwind CSS Configuration Blueprint

When initializing or modifying the frontend, use this exact theme extension configuration:

```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./index.html"
  ],
  theme: {
    extend: {
      colors: {
        ink: "#14110F",
        soot: "#1D1915",
        ash: "#332D26",
        bone: "#E8E1D2",
        dust: "#8C8576",
        amber: {
          sherlog: "#E0A63A"
        },
        vermilion: "#E4572E",
        verdigris: "#4FA38B",
        slate: {
          sherlog: "#8FA3C7"
        },
        oxblood: "#8E2F3C"
      },
      fontFamily: {
        sans: ["Inter", "Space Grotesk", "sans-serif"],
        mono: ["JetBrains Mono", "IBM Plex Mono", "monospace"]
      },
      borderWidth: {
        '1': '1px'
      }
    }
  },
  plugins: []
};
```
