# django-query-optimizer — Design contract

Optional Django Admin surface. Preserve host admin navigation, permissions, component semantics and theme compatibility; no separate application shell.

## Priority journeys

1. Inspect captured query sessions in Django Admin.
2. Find repeated or slow queries.
3. Open source evidence without losing filters.

## Existing sources and visual ownership

- [README.md](README.md)
- [src/django_query_optimizer/templates/django_query_optimizer/admin/change_list.html](src/django_query_optimizer/templates/django_query_optimizer/admin/change_list.html)

Preserve existing host components and semantic styles. Do not invent a replacement
palette, navigation shell or brand during an unrelated change. Define token ownership
before new custom styling; keep current implementation facts separate from requirements.

## UX acceptance and verification

- Make the primary task visible; preserve navigation, filters, input and focus across updates.
- Define loading, empty, validation error, unavailable dependency, stale data and recovery
  states where relevant. Never display a failed operation as successful.
- Use text or icons with labels as well as colour for status. Keep keyboard focus visible,
  navigation predictable and motion optional; respect reduced-motion preferences.
- For web content, target WCAG 2.2 AA; use at least 4.5:1 contrast for ordinary text
  (3:1 for qualifying large text), and aim for 44 CSS px touch controls. Verify the
  complete applicable standard, not only these examples. Apply equivalent native
  accessibility APIs to desktop controls; do not claim web certification for a native UI.
- Test the primary journey, empty data, a failed operation and recovery at representative
  viewport/window sizes. Verify keyboard use, long labels and realistic data volumes.
  Keep screenshots or other reproducible evidence with the UI change; document checks
  that could not run. Static lint is not evidence of usability or accessibility compliance.
- Maintain provenance and licence records for fonts, icons, artwork and generated assets;
  serve assets locally where feasible. Do not copy a reference brand's logos or identity.
- Keep detailed journeys/acceptance evidence in existing project documentation. Update
  this contract alongside UI changes; preserve existing component and token ownership.


## Agent use

Read this contract before changing the human-facing surface. It is an on-demand
reference, not an automatically injected file. Prism may lint its size, imports and
local references without claiming visual, ergonomic or accessibility certification.
