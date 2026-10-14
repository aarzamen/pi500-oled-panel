# Companion application plan

**Future implementation plan.** The companion below is proposed; this document
adds no service to the current OLED runtime or installation. It explains the
existing application indicator and gives a future coding agent a bounded path
to richer information on the OLED.

## What “App Not configured” means

The OLED software is already the application that reads the buttons, collects
host metrics, draws the seven pages, and handles the existing controls. The
Home page's `App Not configured` line means that its optional **workload
monitor** has no selected target. It does not check which applications are
installed on the computer.

The default is `"workload": null` in [config.example.json](../config.example.json)
and [config.py](../oled_panel/config.py). This is a valid standalone setup.
CPU use, RAM, temperature, network information, root storage, uptime, and the
supported Pi power readings already have collectors. A companion daemon is
useful for information those collectors cannot know: the name of a particular
job, its measured progress, a required device's connection, or the last
successful backup.

The existing optional PanelBridge integration is a separate development feature
in source version `0.1.1.dev1`. Its rollout is parked and it has not been deployed
as a combined OLED setup. This plan does not resume it. See the preserved
[PanelBridge boundary](panelbridge.md).

## What can be configured today

These are valid minimal configuration objects; omitted device settings use the
defaults. When applying a workload value, retain the verified settings in the
device's complete configuration.

```json
{"workload": null}
```

```json
{"workload": {"type": "service", "name": "example.service"}}
```

```json
{"workload": {"type": "endpoint", "url": "http://127.0.0.1:8080/health"}}
```

The service name and URL are examples, not installed targets. The current
[collector](../oled_panel/metrics.py) reports these results:

| Configuration | Measurement | OLED state and limit |
| --- | --- | --- |
| `null` | No workload check | `Not configured`; host telemetry still works. |
| `service` | `systemctl is-active NAME`, with a 0.4-second timeout | `Ready` only when the command succeeds and says `active`; `inactive` or `failed` gives `Stopped`; other results give `unavailable`. This checks a system service, not an application's internal health. |
| `endpoint` | HTTP(S) request, with a 0.4-second timeout | An obtained response with status 200–399 gives `Ready`; other responses and caught request failures give `unavailable`. The standard URL opener normally follows redirects. The response body is never read. |

An HTTP 200 response containing `{"state":"error"}` would therefore still
produce `Ready`. Selecting a JSON URL does not add task details or JSON parsing.
The current UI renders only `workload_state`, under the generic `App` and
`Application monitor` labels. It does not render a configured service name,
application name, message, or progress value. The existing sample freshness limit
of three seconds protects host telemetry; it does not establish the freshness of
an application's unseen internal state.

For an installed OLED, editing `config.local.json` in the source checkout does
not change `/etc/oled-panel/device.json`. Follow the configuration and recovery
procedure below before making an installed change.

## First useful companion

Build a small same-host service, provisionally called `oled-companion.service`.
It runs independently of graphical login, so it can report a job that continues
in Headless mode or after Stop Desktop. Prefer Python 3.12 or 3.13 and the standard
library for the initial HTTP server and schema; use a project environment created
with `uv`.

The companion gathers application-specific observations and serves a cached
snapshot on `127.0.0.1`. The existing OLED process remains the sole dashboard
owner of the display and buttons; the startup selector retains its existing
separate boot phase. The companion never opens GPIO or I2C, drives the screen,
invokes the OLED action helper, or changes Desktop, boot, or power state.

A real workload supplies its status through an explicitly configured, bounded
local record or a read-only adapter. Task progress must come from completed work,
such as 37 verified files out of 100. A running process or elapsed time cannot
stand in for that measurement. There is no arbitrary shell-command adapter,
command field in the status schema, or action route in the HTTP service.

## Proposed local interface

Port `8766` is a proposed default. Check that it is free on the selected host
before implementation and document any chosen replacement. Bind only to numeric
IPv4 loopback for the first version; this is a local status feed.

| Request | Proposed response | Meaning |
| --- | --- | --- |
| `GET /health` | HTTP 200 with a tiny readiness result, or HTTP 503 | 200 requires a fresh companion collection loop and `ok` or `busy` aggregate status for the enabled adapters. With all adapters disabled, it proves only that the companion is ready to serve. |
| `GET /v1/status` | HTTP 200, `application/json`, at most 8 KiB | A diagnostic snapshot, including degraded, stale, error, or unknown states. 200 means the document was served, so this route must be parsed. |
| Other paths or methods | HTTP 404 or 405 | No command execution or control API. |

Disabled adapters are omitted and do not count as failed checks. Enabled adapters
must have explicit readiness rules. For example, an observed idle task can be
`ok`; a required device that is absent is `degraded`. A startup snapshot is
`unknown` until the first collection completes. Serve cached results immediately;
HTTP handlers must not wait for a device probe, backup operation, or slow job.

After that service exists, the **current** OLED can monitor only its readiness
with this existing configuration format:

```json
{"workload": {"type": "endpoint", "url": "http://127.0.0.1:8766/health"}}
```

This would display the existing `Ready`/`unavailable` indicator. Rich information
requires the reader and UI work in Phase 3.

### Proposed version 1 snapshot

The example uses synthetic observations. Its date is part of a test fixture,
not evidence of a job that ran on a device.

```json
{
  "schema_version": 1,
  "instance_id": "02c03195-27df-4c1c-b680-9fe23b6dc06c",
  "sequence": 42,
  "observed_at": "2026-10-14T12:00:00Z",
  "ttl_s": 10,
  "name": "File sync",
  "state": "busy",
  "summary": "Copying verified files",
  "task": {
    "name": "Nightly copy",
    "state": "busy",
    "completed": 37,
    "total": 100,
    "unit": "files",
    "observed_at": "2026-10-14T12:00:00Z",
    "ttl_s": 10
  },
  "checks": [
    {
      "id": "backup-volume",
      "label": "Backup volume",
      "state": "ok",
      "value": "32 GiB free",
      "observed_at": "2026-10-14T11:59:59Z",
      "ttl_s": 30
    }
  ],
  "messages": [
    {
      "id": "copy-started",
      "severity": "info",
      "text": "Nightly copy started",
      "observed_at": "2026-10-14T11:59:55Z",
      "ttl_s": 30
    }
  ]
}
```

Freeze these rules in fixtures and parser tests before implementing the server:

- `schema_version` is integer 1. A different major version is unavailable to
  this reader. Define the required fields and permitted optional additions.
- `instance_id` is a fresh random UUID at service startup. It identifies a
  producer run, not the host. `sequence` is a nonnegative integer that advances
  when a new collection completes, never just because an HTTP request arrived.
- All timestamps are UTC with `Z`. Each TTL is an integer from 1 to 300 seconds.
  A new top-level snapshot must retain the actual task/check observation times;
  it must not make an old job record fresh by rereading or repackaging it.
- `state` is one of `ok`, `busy`, `degraded`, `error`, `stale`, or `unknown`.
  Aggregate enabled task/check states in this order: error, stale, degraded,
  unknown, busy, ok. Messages do not change readiness; their producing adapter
  records any operational failure as a task/check state.
- `name`, labels, and IDs are at most 32 printable characters; `summary` is at
  most 64; check values and message text are at most 96. Use display-safe text
  and reject control characters. Limit checks to eight and messages to four.
- `task` can be `null`. Known progress uses integers with
  `0 <= completed <= total` and `total > 0`; unknown progress uses `null` for
  both counts. Reject booleans as numbers, negative values, and impossible
  totals. A progress percentage is derived only from valid, fresh counts.
- Messages have `info`, `warning`, or `error` severity and their own expiry.
  They describe observations. They cannot request actions. Keep secrets, raw
  logs, patient details, and identifying device paths out of the feed.

Freshness must be computed by the consumer as well as the producer. Reject
timestamps more than two seconds in the future. Mark expired observations
`stale` and recompute aggregate state; never continue to show them as Ready or
Busy. Use monotonic time since receipt and time since sequence advancement to
catch a frozen producer even if the local wall clock changes. Reset sequence
tracking when `instance_id` changes. On a request or parser failure, show
`unavailable`; any retained values must be explicitly labeled as last seen.
Repeated successful HTTP responses must not refresh the age of an unchanged
observation.

## Tasks for a future coding agent

### Phase 1 — lock the contract and existing behavior

Read [config.py](../oled_panel/config.py), [metrics.py](../oled_panel/metrics.py),
[app.py](../oled_panel/app.py), [ui.py](../oled_panel/ui.py), and
[install.py](../system/install.py). Record the source revision and run the
existing suite before changing runtime behavior.

Add focused characterization tests for the current workload choices. Cover
`null`, active/inactive/failed services, command failures and timeouts, accepted
HTTP statuses, HTTP failures, and a 200 response with an unhealthy JSON body.
The latter must demonstrate that the current reader does not inspect JSON.
Existing [metric tests](../tests/test_metrics.py) primarily cover host telemetry;
they do not supply this complete workload contract matrix.

Create good/busy/degraded/error/stale/unknown version 1 fixtures and a pure
validator. Test malformed or oversized JSON, wrong field types, unsupported
versions, invalid progress, string/array limits, timestamp skew, repeated
sequences, and producer restarts with injected clocks. Validate all documented
configuration examples against the corresponding current or proposed loader.

**Exit check:** the baseline suite passes and the future protocol has executable
fixtures. No device operations are needed for this phase.

### Phase 2 — implement the companion independently

Add a small companion package, proposed as `oled_companion/`, with separate
schema, collection, adapter, and server modules. Update packaging deliberately;
the current package discovery includes only `oled_panel*`. Give it a complete
foreground entry point for local testing and a systemd entry point for later
installation.

Collect on a one-second cadence into a bounded latest-result cache. Isolate
adapter failures, set deadlines, and avoid an unbounded backlog of probes.
Ensure a stalled collector makes `/health` return 503 rather than serving a
permanent success. Start with a fixture-backed task record so all behavior can
be tested without Linux hardware. Do not ship invented progress as live data.

Test the actual loopback server: bind address, route/method behavior, content
type, byte limits, startup readiness, adapter failure, collection stalls,
shutdown, and fresh recovery. An active systemd unit alone is insufficient
validation of these behaviors.

**Exit check:** a local client sees changing, correctly timestamped snapshots
and readiness failures. The current OLED's `/health` monitor can be demonstrated
with mocks or local HTTP fixtures; no installed OLED configuration changes occur.

### Phase 3 — add a rich OLED reader and Workload display

Add an explicit third workload type, proposed as `companion`, to the validated
OLED configuration. This example is **not accepted by today's loader**:

```json
{"workload": {"type": "companion", "url": "http://127.0.0.1:8766/v1/status"}}
```

Keep `null`, `service`, and `endpoint` working as documented. For the new type,
require a numeric loopback URL, reject embedded credentials and redirects, and
apply an 8 KiB body limit and a 0.4-second total request deadline. Do not let proxy
environment settings turn the local request into an external one. Parse and
validate JSON before publishing it to the UI.

Use a bounded worker/cache so a slow feed does not delay key polling, rendering,
or other host collectors. Keep companion observation time separate from the
fresh host snapshot time. Publish normalized name, state, summary, task, checks,
and messages; apply their independent expiry on every render.

Preserve the seven standalone pages and put the richer view inside Workload.
Keep Home's compact app state. Workload can show `File sync`, `Busy`, `37/100
files`, and a short summary; K3 details must make every bounded field reachable,
including age and failure reason. Label unknown progress and last-seen values
explicitly. Producer text cannot create a menu item or an action.

Extend [UI tests](../tests/test_ui.py) and [app tests](../tests/test_app.py) for
128×64 one-bit frames, long names, detail navigation, expired fields, missing
companions, malformed data, and a frozen server. Retest wake-only first press,
60-second blanking, release-before-confirmation, two-second action holds,
action-error display, and the existing action allowlist. Keep boot chooser,
Desktop fallback, and saved-default behavior covered by their current tests.

**Exit check:** rendered previews and tests demonstrate useful details and
failure states while the existing pages and controls retain their behavior.

### Phase 4 — add one useful adapter at a time

| Adapter | Evidence it reads | Required validation |
| --- | --- | --- |
| Task progress | A configured local job record with producer heartbeat, task state, measured completed/total counts, and observation time | Atomic producer writes; bounded reads; missing/stale/partial records; restart and completion; unknown totals. |
| Device connectivity | Read-only observation of a specifically configured device or connection | Distinguish detected, connected, and actually working; an address or USB node alone does not prove useful output. |
| Backup freshness | The real backup application's successful-completion receipt and timestamp | A file's modification time alone does not prove success; an old last-success event must breach a configured maximum age even while the companion is fresh. |
| Storage | Free space and mount identity for a selected workload volume | Missing mounts, permissions, low-space thresholds; root filesystem space is already built in. |
| Messages | A bounded record from the workload with severity and expiry | No raw log tail; expired messages disappear; empty and oversized records stay bounded. |

Choose the first actual workload with the user before implementing its adapter.
Require a trusted, explicitly configured local path and safe ownership for file
inputs; reject unexpected symlinks and oversized records. A system-service
observation can be another check, but internal health needs its own evidence.
Do not mark an unconfigured adapter as a missing installation dependency.

**Exit check:** each enabled adapter has real producer evidence, clear failure
states, and tests. Adding CPU or temperature polling is unnecessary for this
OLED use case.

### Phase 5 — stage installation and recovery

Create an independent systemd unit under an existing nonroot account. It should
start under `multi-user.target`, use restart limits, and have a bounded shutdown.
Stage and inspect protections such as `NoNewPrivileges=yes`, `PrivateDevices=yes`,
and filesystem access limited to its configured read inputs and its own runtime
directory. It needs no new GPIO permissions or sudoers entry. Test those settings
on the selected Linux host before claiming an installed service works.

The companion must not become a prerequisite for the selector, Desktop, or
`oled-panel.service`. Its absence is a workload status failure, never a blocked
boot or a reason to change the saved Desktop default. Give its installation an
independent inventory and recovery record for only its own paths. Preserve the
OLED installer's existing ownership records.

The current OLED installer:

- Copies source configuration to `/etc/oled-panel/device.json`; the daemon reads
  that installed file when it starts.
- Records owned files, permissions, ownership, and SHA-256 digests in
  `/var/lib/oled-panel/install-backup/manifest.json`.
- Refuses existing owned paths and backup directories; it is not an automatic
  upgrade tool.
- Stops uninstall on unexpected installed-file edits. Only the supported saved
  default change is specially allowed.

For the first deliberate OLED configuration change, follow
[Uninstall and configuration changes](setup.md#uninstall-and-configuration-changes):
stop the panel services, complete the verified uninstall, retain/archive its
backup under a unique name, edit source configuration, check it, stage into a new
directory, and reinstall. Installation initializes the saved default to Desktop.
Do not overwrite the manifest, alter stored digests to conceal changes, or run
the installer over the existing installation. Test companion uninstall and OLED
uninstall independently, including interrupted work and unrelated files.

Preserve the Pi 500 model guard. Any future PanelBridge work still requires its
matching enrolled desktop account and capability receipt. This companion does
not bypass those checks or establish Pi 5 or Jetson compatibility. Board-specific
ports require a separate resumed task and physical validation.

## Future button transport backend

The [hardware sourcing notes](hardware-sourcing.md) track the user-supplied
ACEIRMC B0GWQPY2C7 source board and Dorhea B0GWTWPMNT candidate. The ACEIRMC
listing describes an eight-pin I2C display with four independent keys; Dorhea
explicitly lists I2C plus independent K1–K4. Neither listing documents an onboard
button expander or establishes that the buttons travel over I2C. A four-wire
connection for power, display, and buttons would need a bus-based button
transport, such as an onboard I2C GPIO expander.

Current [PanelHardware](../hardware_check.py) creates four GPIOZero `Button`
objects on individual BCM pins, with configured pull-ups and 30 ms debounce.
A future agent can extract a `Buttons` interface with `read_keys()` and `close()`,
then implement direct-GPIO and verified I2C-expander backends. The display and
button ownership stays in the panel process.

Before buying or adapting a board, confirm the button chip, register protocol,
I2C address and shared-bus compatibility, 3.3 V logic, pull-ups, polarity, and
debounce behavior from reliable hardware documentation. Measure the new PCB,
screen, buttons, and connector clearances for its own case fit. Add a dedicated
board profile with verified wiring and backend settings; test press/release,
held keys, simultaneous keys, and bounded bus-failure handling. Preserve the
model guard until that profile has separate physical validation.

This hardware extension is independent of the companion data service and the
parked PanelBridge rollout. The current Dorhea candidate does not establish a
reduction in button wiring.

## Validation and handoff checklist

- [ ] Existing tests pass before changes; new protocol, HTTP, adapter, UI, and
      installation tests pass afterward.
- [ ] Source archives/wheels contain the companion when intended, and a clean
      environment can import/run it without GPIO access or private inputs.
- [ ] Previews cover ready, busy, degraded, error, stale, unavailable, and
      unconfigured states with readable details and all seven standalone pages.
- [ ] A local integration test kills, stalls, restarts, and corrupts the producer;
      cached Ready/progress values expire and fresh values recover.
- [ ] Staged units and recovery records validate; configuration edits are applied
      through the documented recovery path and preserve previous backups.
- [ ] After a separately authorized deployment, observe the selected host's
      systemd unit, HTTP readiness, parsed status, and actual OLED output.
- [ ] On that host, confirm the real workload's counts/device/backup receipts
      match the OLED and that failures become visible within the chosen TTL.
- [ ] Report source/test, installation, and physical OLED/workload evidence
      separately. Record the host, revisions, and remaining limitations privately.

Physical device work and a resumed PanelBridge rollout are outside this
documentation task. Passing fixtures or seeing an HTTP response does not prove
that a future application or attached device works.

## Current source map

| Source | What a coding agent should inspect |
| --- | --- |
| [config.py](../oled_panel/config.py) | `DEFAULT` and `load_config`: optional `workload`, accepted types, service/URL validation. |
| [metrics.py](../oled_panel/metrics.py) | `_workload_state`, `collect_snapshot`, `is_fresh`: current indicator, built-in telemetry, host sample timestamps. |
| [ui.py](../oled_panel/ui.py) | `PAGES`, `_detail_fields`, `_lines`, `is_render_fresh`: seven pages, generic app label, three-second host freshness. |
| [app.py](../oled_panel/app.py) | `_sample_loop`, `run_foreground`, `dispatch_action`: independent collection, rendering/key loop, fixed action forms. |
| [install.py](../system/install.py) | `render`, `install`, `uninstall`, `validate_panelbridge_integration`, `preflight`: installed configuration, recovery digests, enrollment/receipt and model guards. |
| [pyproject.toml](../pyproject.toml) | Development version, dependencies, and current package discovery. |
| [setup guide](setup.md), [validation guide](validation.md), [PanelBridge guide](panelbridge.md) | Current deployment procedure, evidence limits, and parked integration. |
