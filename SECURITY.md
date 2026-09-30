# Security Policy

## Supported versions

Security fixes target the current Windows web channel, the current supported Windows desktop channel, and the current Android channel. Legacy builds may receive compatibility guidance only.

## Report privately

Do not open a public issue for a vulnerability. Use GitHub private vulnerability reporting:

https://github.com/styayur/LGXT-Assistant/security/advisories/new

Never include platform passwords, AI API keys, student identifiers, private course data, or unredacted AI conversations. Provide the affected channel/version, Windows or Android version, reproduction steps, impact, and minimal proof-of-concept details.

## Security-sensitive areas

Reports about credential storage, local web-server binding, browser-to-native bridges, export path handling, arbitrary file access, update/release integrity, dependency compromise, or accidental transmission to the wrong AI provider are in scope.

The Windows web build starts a local service for the current user. It is intended to bind to loopback, not a public or LAN interface. The desktop app uses the operating-system credential store; public issues must not contain credential material.
