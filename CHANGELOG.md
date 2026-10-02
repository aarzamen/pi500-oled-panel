# Changelog

## 0.1.1.dev1 — development

- Add optional same-host PanelBridge startup choices and monitor status,
  start/stop and display-trial controls.
- Keep controller requests off the OLED input thread and disable actions when
  status is stale or unavailable.
- Require matching desktop-account enrollment and a supported PanelBridge
  capability receipt before enabling integration.
- Preserve standalone defaults, the Pi 500 model check and restoration records.

This integration is software-tested. Hardware deployment is deferred.

## 0.1.0 — 2026-10-02

- Publish the Pi 500 OLED dashboard, Desktop/Headless chooser, bounded system
  actions and recovery/uninstall tools.
