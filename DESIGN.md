# django-query-optimizer — Design contract

> Contract for the library's one human-facing surface: the read-only **Query Optimizer
> dashboard inside Django Admin**. Rule: [standards/rules/design.md](standards/rules/design.md);
> method and acceptance criteria: the shared-standards *DESIGN-CONTRACT* guide. Read it before
> changing the admin template, its context or the wording it shows; update it in the same change.
>
> Status: **[implemented]** links the code · **[decided]** names the decision · **[proposed]**
> is not agreed. This file documents the current surface; it does not redesign it.

## 1. Surface and status

- **Surface:** Django Admin customisation — one changelist page registered on an unmanaged
  `QueryLog` model, rendered from the in-process `QueryStore`. **[implemented]**
  ([admin/\_\_init\_\_.py](src/django_query_optimizer/admin/__init__.py),
  [change_list.html](src/django_query_optimizer/templates/django_query_optimizer/admin/change_list.html),
  [store.py](src/django_query_optimizer/store.py))
- **Other outputs (not graphical):** pytest fixtures and assertion messages
  ([pytest_plugin.py](src/django_query_optimizer/testing/pytest_plugin.py)) and a SARIF 2.1.0
  report ([sarif.py](src/django_query_optimizer/reporting/sarif.py)) that the separate VS Code
  extension turns into editor diagnostics. Their human surface is owned by that extension.
- **Lifecycle:** prototype — version `0.1.0a1`, README status *pre-alpha*; the admin dashboard is
  marked done (phase 1c) in [README.md](README.md). A WebSocket "live dashboard" is only listed
  as a future `realtime` extra (phase 4). **[proposed]**, not built.
- **Detailed specs:** none. Runnable demo: [examples/demo/README.md](examples/demo/README.md).

## 2. Users, devices and priority tasks

| User | Context and device | Priority tasks |
| ---- | ------------------ | -------------- |
| Django developer | Desktop browser on a development server, staff/superuser login, while reproducing a slow view | 1. see which endpoints issue the most queries · 2. spot slow requests (≥ 500 ms) · 3. see how many recommendations exist per severity |

Primary action: read the summary cards, then the *Recent requests* table. The page has no
mutating action: add, change and delete permissions are refused. **[implemented]**

## 3. Journeys and navigation

- **J1 — Inspect captured traffic:** add the app and `QueryOptimizerMiddleware` to development
  settings → exercise the site → Admin → *Query Optimizer* → summary cards, recommendations by
  severity, top 10 endpoints, last 50 requests (newest first). **[implemented]**
  Failure: middleware missing → *Top endpoints* says how to enable capture. **[implemented]**
- **J2 — Find slow requests:** the slow-request card counts requests ≥ 500 ms; in *Recent
  requests* their duration is bold red. **[implemented]**
- **J3 — Open one request's queries and recommendations:** not available; the details are only
  reachable through tests, SARIF or the VS Code extension. **[proposed]** a read-only detail view
  per request with SQL, call site and suggestion.
- **Information architecture:** one page under the app's admin section, admin breadcrumbs from
  `admin/base_site.html`; no filters, search, sorting or pagination. **[implemented]**
- **Density:** compact admin tables; numbers and endpoints only. Fits an expert, occasional check.

## 4. Identity

None of its own: the page inherits the host Django Admin chrome and `.module` blocks.
**[implemented]** No logo, palette or font is added, and none should be: the host project's
admin identity wins. **[decided]** by the Django Admin row of the shared-standards
*DESIGN-CONTRACT* guide.

## 5. Tokens and components (owned elsewhere)

| Concern | Source of truth | Rules of use |
| ------- | --------------- | ------------ |
| Colour, type, spacing, light/dark | Host Django Admin stylesheet and its CSS variables | reuse admin variables and classes; add no palette |
| Layout of summary cards | inline `style` in [change_list.html](src/django_query_optimizer/templates/django_query_optimizer/admin/change_list.html) | flex row, wraps at 160 px per card |
| Severity names | `Severity` in [recommendations/base.py](src/django_query_optimizer/recommendations/base.py) | lowercase values (`critical`, `high`, …) |
| Thresholds | `SLOW_REQUEST_MS`, `MAX_REQUESTS` in [store.py](src/django_query_optimizer/store.py) | page wording must match these constants |

- **Shared contract:** `contract.css` not imported, `@chrysa/ui` not used — correct for an
  admin plug-in.
- **Design debt and drift:** the template hard-codes `#666`, `#ba2121`, `#e07b39` and font sizes
  inline instead of admin variables; "≥500 ms" is repeated as a literal in the template.

## 6. Interaction and states

- **Component states:** host admin defaults; the page has no own controls.
- **Action feedback:** none needed (read-only).
- **Data states:**

  | State | Where it appears | Behaviour |
  | ----- | ---------------- | --------- |
  | Loading | whole page | server-rendered; no placeholder needed |
  | Empty | *Top endpoints*, *Recent requests* | explicit text; the first one explains how to start capture **[implemented]** |
  | Error | — | no handled state; a store or template failure is a Django error page |
  | Offline / unreachable | — | not applicable (server-rendered) |
  | Stale data | whole page | not shown: the buffer is per process, keeps the last 500 requests and is lost on restart; the page does not say so **[known gap]** |
  | Reconnect | — | not applicable |

- **Real-time:** none; the user reloads the page. **[implemented]**
- **Motion:** none, consistent with the admin host. Entrance motion (FE-053) is not imposed
  inside Django Admin.

## 7. Responsive and support conventions

Follow Django Admin conventions (≥ 4.2): base template, breadcrumbs, `.module` sections, admin
tables. Cards wrap on narrow screens; wide tables rely on the admin's own overflow. Do not add a
custom SPA shell or navigation inside the admin.

## 8. Accessibility

- **Target:** WCAG 2.1 AA for the page content (canon floor).
- **Keyboard:** only the admin chrome is interactive; nothing to trap.
- **Perception:** severity is written as text, colour only reinforces it. A slow duration is
  marked by bold red only, with no text cue **[known gap]**. Literal colours ignore the admin dark
  theme; `#e07b39` on white is 2.97:1 (below 4.5:1).
- **Assistive technology:** tables have `<th>` headers under an `<h2>`; no `<caption>` or `scope`.
  No screen-reader pass was run.

## 9. Assets

None shipped: no font, icon or image. The admin's own assets belong to the host Django
installation. Package licence: MIT ([LICENSE](LICENSE)).

## 10. Acceptance criteria and evidence

- **Criteria:** the page renders inside the admin base with breadcrumbs; every section has an
  explicit empty state; slow requests and severities are identifiable without colour; text stays
  readable in the admin light and dark themes; thresholds shown match `store.py`; no add, change
  or delete control appears.
- **Tests:** [tests/unit/test_admin.py](tests/unit/test_admin.py) covers permissions and the
  context (keys, empty store, newest first, cap at 50); the rendered HTML is not tested.
- **Evidence log:**

  | Date | Change | Checks run (tool, sizes, modes) | Result | Not run, and why |
  | ---- | ------ | ------------------------------- | ------ | ---------------- |
  | 2026-11-08 | contract written from the code | source review | gaps listed in §11 | no browser run: documentation-only change |

## 11. Open choices, known gaps and maintenance

- **Known gaps:**
  - Severity highlighting never applies: the template compares keys with `"HIGH"`, `"CRITICAL"`
    and `"MEDIUM"`, but `Severity` values are lowercase.
  - The *Time (UTC)* column is rendered through Django's time-zone conversion, so it shows local
    time when `TIME_ZONE` is not UTC.
  - *Avg queries / request* is rounded to an integer in *Top endpoints* (`widthratio`) but shown
    with one decimal in the card.
  - No per-process / buffer-size notice (stale data), no drill-down (J3), no rendered-HTML test.
  - Hard-coded colours do not follow the admin dark theme.
- **Open choices:** **[proposed]** replace inline styles with admin CSS variables and a small
  template stylesheet; **[proposed]** add a text "slow" marker next to the duration.
- **Maintenance:** the library maintainer updates this file with any change to the admin
  template, its context keys or the thresholds in `store.py`.
