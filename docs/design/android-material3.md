# Android Material 3 design and skill review

Source: https://github.com/skydashnet/material-design-3-ui-skill
Pinned commit: `82783f76de4a5b08a60421cae935cf8de7ca1ee8` (reviewed 2026-11-18).
MIT, copyright 2026 Material Design 3 UI Skill contributors. Vendored declarative
guidance and original LICENSE in `material3-skill/`. No installer executed.
Reviewed SKILL.md, navigation, forms and accessibility. The upstream tree includes
install/uninstall shell scripts and a validator; none is required by the app.

Intent: students continuing unfinished assignments with one hand. Deadline-ordered
unfinished work is the focal content, then completion progress, then courses and
offline material. Do not treat missing grades, attempts or deadlines as known.

Hierarchy: a headline task count, readable assignment titles, course/deadline
metadata, and a direct open action. Partial network failures must remain visible.
Palette: semantic Material roles generated from the existing academic blue seed.
Surfaces: surface, surfaceContainerLow and secondaryContainer, using tonal
separation. No decorative shadows. Cards contain related editing/form content;
assignment lists use Material ListTile rows.
Typography: platform default, 28 headline, 20 section, 16 body, 14 metadata. No
fixed-height text blocks; long labels wrap. Four-level hierarchy uses weight and
semantic text colors. Spacing: 4-unit grid, 16 outer padding and 8/12/16 gaps.

Component map: bottom NavigationBar for four destinations; FilledButton for login
and saving; outlined/text buttons for secondary actions; TextField for notes;
ListTile for course/task selection; LinearProgressIndicator for measured completion;
AlertDialog for transport consent and destructive/transactional confirmation.
SafeArea and a scrolling body preserve system/IME insets. Buttons target 48dp or
larger; icon-only controls have tooltips. System light/dark mode uses semantic
roles. Formula preview remains safe editable LaTeX source; no untrusted web image
loading or unmeasured rendering engine is introduced.

Session storage: optional device-encrypted token/cookies via flet-secure-storage,
never a password. The API origin is pinned within the stored envelope and a fresh
userInfo check validates restoration. Local note schema 1 and exported backup
format are unchanged. Secure storage failure falls back to manual login; no
plaintext session fallback. Logout invalidates in-flight work and deletes storage.
HTTP still requires an explicit remembered choice and persistent warning.

Verification must distinguish browser renders, synthetic native fixtures and real
platform login. Screenshot/large-text/native results are recorded in the release
evidence rather than assumed from design tokens.
