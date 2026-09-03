# report

## ADDED Requirements

### Requirement: Report themes

Report generation SHALL accept a theme - a builtin name (`bokken`, `plain`)
or a JSON file with brand color, dark variant, brand label, and footer -
that changes deliverable chrome and never content: the HTML report's accent
palette, brand label, and footer are themed via a CSS custom-property
override, and the deck carries the themed label and footer. Theme colors
SHALL be validated as `#rrggbb` and an unknown theme SHALL refuse with exit
2. A theme chosen at session creation SHALL be journaled in the config
snapshot and honored by every later export, so regenerated reports are
stable; an explicit `--theme` on export overrides for that export only.

#### Scenario: A consultant white-labels the deliverable

- **WHEN** `bokken export retention --theme acme.json` runs with a valid theme file
- **THEN** the HTML report carries the theme's accent color, brand label, and footer, and the run's content is byte-identical apart from that chrome

#### Scenario: Themes cannot lie

- **WHEN** a theme file carries a non-hex color or an unknown builtin name is passed
- **THEN** the export refuses with exit 2 before writing anything
