# Canonical architecture and channel boundaries

LGXT Assistant is one product with several clients sharing Python domain behavior. This document defines the architecture to prevent new work from accumulating across legacy and current paths.

## Current channels

| Channel | Entrypoint | UI boundary | Release status |
| --- | --- | --- | --- |
| Windows desktop | `default.pyw` | `desktop/` bridge + built `frontend/` React UI | Current supported desktop channel |
| Windows web | `web_app.py` | built `frontend/` served by the local Python process | Current supported Windows web channel |
| Android | `mobile/src/main.py` | Flet client | Separately versioned Android channel |
| Legacy Tk | `default.pyw --legacy` | `ui/` package | Compatibility support; not the target for new product work |

## Core domain

`api.py`, `tasks.py`, `exporter.py`, `config.py`, and the desktop storage/service modules own platform login, course/assignment retrieval, export orchestration, preferences, and local persistence. UI clients should call these boundaries instead of duplicating remote protocol or storage behavior.

## UI boundary

- `frontend/src/` is the React UI source for desktop and web.
- `desktop/bridge.py` is the trust boundary between the local web view and Python.
- `mobile/src/main.py` owns Android navigation and mobile-specific rendering.
- `ui/` owns the legacy Tk interface and should receive compatibility fixes only unless a migration is explicitly planned.

## Persistence boundary

Desktop data lives under `%APPDATA%\LGXT-Assistant`. Credentials use the operating-system credential store, not plain project files. Web mode must not silently create a second competing source of truth; shared storage behavior must be explicit and documented.

## External service boundary

The LGXT platform is accessed through the user's own account. AI requests go only to the provider configured by the user, using that provider's endpoint and key. The local web service binds to loopback by default and is not a public server.

## Extension points

- New AI providers should use the existing provider abstraction rather than branching in every React component.
- New export formats belong behind the exporter/service boundary.
- New channels must document storage, credential, packaging, and release-version behavior before implementation.
- New legacy features must not bypass the current desktop/web bridge.

## Release boundary

Channel versions may differ. Release asset names must identify platform and channel, and release notes must state known limitations. No workflow may publish a build from an untagged or unverified source state.
