# Changelog

All notable blueprint changes are documented here. The `main` branch remains
the update channel for Home Assistant imports.

## AWTRIX NG 1.0.0 - Unreleased

### Added

- Separate AWTRIX NG DWD weather warning blueprint.
- Pushed-app, sound, availability, and MQTT discovery support.
- Multiple current-warning and optional preliminary-warning sensors.
- Compact region labels when more than one distinct region is selected.
- Recovery after Home Assistant and AWTRIX restarts without recovery beeps.
- Blueprint version displayed at the beginning of the description.

## AWTRIX 3 2.0.0 - Unreleased

### Added

- Multiple current-warning and optional preliminary-warning sensors.
- Compact region labels when more than one distinct region is selected.
- Blueprint version displayed at the beginning of the description.

### Changed

- The fixed app name is now `dwd-warnings` instead of `jc-23`.
- Existing blueprint path and input identifiers remain compatible with existing
  automations; legacy scalar sensor inputs are normalized to lists.
- Beeps occur only for a new warning above the configured threshold or a
  severity escalation.
- Startup and periodic updates restore the display app without playing a sound.

### Fixed

- Change-only signatures no longer lose values at Jinja loop scope boundaries.
- No-warning payloads are actually empty instead of containing two apostrophes.
- Optional preliminary-warning sensors trigger their own updates.
- AWTRIX device filters combine integration, manufacturer, and model correctly.
- Missing MQTT topic entities no longer cause an out-of-range template access.

## Repository

### Added

- Automatic AWTRIX 3 and AWTRIX NG icon upload with an explicit firmware
  fallback.
- Payload, change-detection, multi-region, topic, icon, and upload-script tests.

### Changed

- Published repository URLs now use the `main` branch.
