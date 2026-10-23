# Editor selection, data conversion and dependency review

Checked 24 October 2026 using authenticated GitHub CLI stars, upstream repositories and npm metadata. All four requested candidates are starred by the authenticated user. No private stars or account data are stored here.

| Candidate | Upstream / current package | License | Fit and costs |
| --- | --- | --- | --- |
| Tiptap | [ueberdosis/tiptap](https://github.com/ueberdosis/tiptap), 3.32.0 | MIT core and selected extensions | React 19 peer support; modular ProseMirror schema; good tables, images, keyboard/history and custom math nodes. Needs our toolbar and Markdown conversion UI. React package 588,528 unpacked bytes; this is not the delivered bundle size |
| Milkdown | [Milkdown/milkdown](https://github.com/Milkdown/milkdown), Crepe 7.22.3 | MIT | Markdown-first, KaTeX, tables, mobile-friendly editing. Crepe 3,464,473 unpacked bytes plus kit, CodeMirror and Vue dependencies; React integration is possible but adds a second component stack for this small boundary |
| Vditor | [Vanessa219/vditor](https://github.com/Vanessa219/vditor), 4.0.1 | MIT | Chinese UI, source/preview/WYSIWYG, math and Markdown; imperative lifecycle needs React adaptation. 23,638,046 unpacked bytes include assets/renderers; avoid default remote renderer loading in a local app |
| BlockNote | [TypeCellOS/BlockNote](https://github.com/TypeCellOS/BlockNote), React 0.56.0 | MPL-2.0 core; XL packages GPL-3.0 or commercial | Strong React block UX, tables, math and format tooling. React package 24,329,707 unpacked bytes; lossy Markdown interop and block schema require a larger conversion boundary. No XL package installed |

The repositories were not archived. GitHub reported recent pushes for all four (18–24 October 2026 Singapore dates). Maintenance activity is a point-in-time observation, not a support guarantee. Package unpacked size is comparable metadata, not a claim about tree-shaken or gzipped delivery. We installed only Tiptap. [React integration](https://tiptap.dev/docs/editor/getting-started/install/react), [Milkdown math/table features](https://milkdown.dev/docs/guide/using-crepe), [BlockNote format limits](https://www.blocknotejs.org/docs/foundations/supported-formats).

## Decision

Use MIT Tiptap 3.32.0 core/react/pm/starter-kit/image/table/markdown at the question solution boundary. Do not replace chat or the file workspace. Build a small toolbar suitable for narrow touch screens. The application remains AGPL-3.0-only; MIT notices and ProseMirror attributions are bundled in [editor notices](third-party-editor-notices.txt). No proprietary Tiptap templates, Pro extensions or cloud service are used.

Tiptap's published mathematics extension requires KaTeX <=0.18.x while this repository uses patched 0.19.x. We did not force peer dependency resolution. A small local inline/block math node renders through existing KaTeX with `trust:false`, bounded expansion and size. Clicking or keyboard-activating a formula edits its LaTeX. This avoids another math runtime or a second editor.

The assignment chunk measured about 541 KB / 171 KB gzip during the first integration build, including the editor and assignment UI. Markdown/KaTeX is a separate shared chunk. Build output is authoritative for later revisions; loading the editor remains behind the course page's lazy import. No mobile keyboard or handwriting accuracy guarantee follows from these bundle measurements.

## Conversion and persistence

- Canonical schema version 1 stores recoverable Markdown, LaTeX source, original raster data, course/work/question IDs, recognized text, corrected content, solution, selected excerpts, answer and timestamps.
- ProseMirror JSON is an editor implementation detail; Markdown keeps documents recoverable without Tiptap. Inline `$...$` and block `$$...$$` math round-trip through local nodes.
- Import is an explicit source-mode action. Raw HTML is escaped; remote Markdown images are rejected. Pasted HTML images are removed; use the bounded local image picker. Source remains visible when conversion fails. Markdown does not promise arbitrary HTML, diagram or custom extension fidelity.
- Question editing does not migrate or overwrite old workspace or chat files. Save atomically and retain `.previous.json`; unknown document schema versions must be preserved and refused on write.
- Word/PDF export supports headings, basic bold, lists, tables, code/source text and the original image. LaTeX remains source. The Markdown sidecar preserves unsupported content; validated embedded editor raster images are included; arbitrary remote images are not fetched.

## Existing dependency security

`npm audit` initially found four low findings through transitive KaTeX <0.18.2. The lockfile now deduplicates KaTeX to the existing patched 0.19.x direct version, tested with Markdown and the editor. No audit severity was excluded.

`pip-audit` found 35 advisories in the baseline-resolved Pillow 12.3.0. Pillow is now >=13,<14. Current ttkbootstrap 2.2.3 and 1.20.4 require Pillow <13; 1.14.7 requires <12. The legacy-compatible 1.10.1 declares Pillow >=8.2 with no upper cap and is pinned, rather than ignoring resolver constraints or shipping vulnerable decoders. It is an older MIT Tk theme library: tests and actual packaged launch must verify compatibility, and modernization of this compatibility dependency remains follow-up work. No large OCR package, vector database, cloud dependency or UI framework was added.
