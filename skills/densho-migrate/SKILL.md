---
name: densho-migrate
description: Convert an existing documentation set (a docs/ folder, a wiki or a vault in Markdown written for GitHub, GitLab, Obsidian, MkDocs, Docusaurus, VitePress, Hugo, Jekyll, or exported from Notion or Confluence) into the Densho Markdown dialect and folder layout, before it is imported into Densho with Import Markdown or connected to Densho's git sync. Use it whenever someone wants to move, migrate, import or sync existing docs into Densho, prepare a repository for Densho's git sync, or repair docs that Densho already mangled on import (lines merged together, [!NOTE] or ::: tip shown as text, footnotes shown as text, folders duplicated with "(2)", README and readme fighting), even if they never say "migrate".
---

# Migrating documentation to Densho

Densho reads a folder of Markdown as a tree of pages and rewrites every file
it takes in into its own dialect. What the dialect cannot read is not
rejected: it is escaped, merged or dropped, silently. With the git sync that
damaged version is also **committed back to the repository on the first
cycle**, under the team's eyes, and every later cycle builds on it.

So the whole job is to convert first, commit once, and only then import or
connect. A migration done after connecting is a repair of what the sync
already rewrote.

## 1. Find out where the docs are going

Ask, or read it from context, before touching a file:

- **Git sync**: a folder of a repository (often `docs/`) stays the source,
  and Densho keeps it in step both ways. The layout rules below are strict,
  because the sync writes the tree back.
- **Import Markdown** (space menu): a one-way import of a zip of the folder.
  Same layout rules, but nothing is written back, so the cosmetic
  normalisations do not matter.

Then find what produced the docs, because that decides which syntaxes to
expect: `mkdocs.yml` (MkDocs admonitions), `docusaurus.config.*` (MDX,
`:::tip`, `sidebar_position`), `.obsidian/` (wiki links, `> [!note]`
callouts), `.vitepress/`, `hugo.toml` or `config.toml` with `layouts/`
(shortcodes), `_config.yml` (Jekyll, Liquid), `SUMMARY.md` (GitBook).

Work on a branch, and ask the team to hold their edits to the docs while you
migrate: a rename landing in the middle of a move is how two spellings of one
folder are born.

## 2. Take the inventory

Run the checker on the folder Densho will read (the synced folder itself,
not the repository root when they differ):

```bash
python3 <this skill>/scripts/check_densho_ready.py docs/
python3 <this skill>/scripts/check_densho_ready.py docs/ --cosmetic   # also what Densho merely normalises
```

It lists every problem as `breaks` (the content or the tree comes out
wrong), `changes` (Densho writes it back differently: decide) or `cosmetic`
(Densho normalises it). Inside a git repository it also reads the index,
where two spellings of one folder can live even on a disk that cannot hold
them.

Show the user the counts per rule and your plan before rewriting hundreds of
files. The decisions that are theirs: renaming files (links from outside the
docs, from code or from bookmarks, will break), dropping a page's leading
`# Title`, and anything lossy (a footnote folded into its sentence).

## 3. Fix the layout

Densho's tree is the folder tree:

- **A page with subpages is a folder**, and the folder's own text lives in
  its `readme.md` (`README.md` is fine, the spelling is kept). A folder
  without a readme still becomes a page, an empty one. An `index.md` or
  `_index.md` playing that role must be renamed to `readme.md`, or it
  becomes a child page called "index".
- **A file is a page named after the file**, without `.md`. A leading
  number with a dash (`10-install.md`) sets the order and is not part of the
  title; without one, pages sort in natural order (2 before 10). Use that
  prefix to keep an existing navigation order (`mkdocs.yml` nav,
  `sidebar_position`, `SUMMARY.md`): the git sync reads only the `NN-` form.
- **One name, one spelling.** `Developer/` and `developer/`, or `README.md`
  and `readme.md`, are one path for Densho, macOS and Windows. Merge them.
  On a case-insensitive disk a case-only rename needs two steps:
  `git mv Developer tmp && git mv tmp developer`. A folder and a file with
  the same name (`Guide/` and `Guide.md`) are two pages with one title, and
  one of them gets "(2)": merge the file into `Guide/readme.md`.
- **Names are written back as titles.** Densho replaces `\ / : * ? " < > |`
  with a space, collapses spaces and cuts names at 80 characters when it
  writes a page file. A name that would change is renamed at the next write:
  rename it now, with its links.
- **Reserved folder names**: `assets`, `synced-blocks`, `.trash` and `.git`
  are never read as pages. Documentation stored in a folder with one of
  those names must move; a note meant to stay out of Densho can stay there
  on purpose (say so in the report). Images and PDFs can stay wherever they
  are, and a folder holding no `.md` file (`img/`) never becomes a page.
- **Only `.md` is read.** Convert `.mdx` (drop the imports, turn the
  components into Markdown). Symbolic links are ignored. Other files are
  left alone, and a relative link to an image or a PDF imports it as an
  attachment, written back to the same path.
- **Do not write `id:` into front matter, or create `.trash/`.** Densho owns
  both, and `sort:`, `order:` and `space:` too. Docusaurus puts an `id:` in
  every doc: remove it once the links that used it are resolved, and turn a
  generator's `order:` into an `NN-` prefix. Other front matter keys are kept in the file by the git sync and
  hidden from the page; `title:` is not the page's title (the file name is),
  so rename the file when the two disagree and the title should win.
- **A page's leading `# Title`** that repeats the file name appears twice in
  Densho, once as the page title and once in the text. Drop it when the user
  agrees.
- **The README at the root** of the synced folder is a page like any other.

## 4. Convert the syntax

Read `references/conversions.md` for the conversion of each construct, with
examples per source tool. The ones that matter most:

- Callouts: `> [!NOTE]`, `> [!tip] Title`, `!!! warning "Title"`, `:::tip`,
  `:::caution` become `:::note`, `:::success`, `:::warning`, `:::danger` or
  `:::info` blocks. Densho callouts carry no title: put it in bold on the
  first line inside. Collapsible ones (`??? note`, `> [!note]-`) and
  `<details>` become `:::toggle Title`. Keep callouts and toggles side by
  side, never one inside the other: Densho writes both with `:::` fences,
  and the inner closing fence ends the outer block on the next round trip.
- **Lines that must stay apart.** A single newline inside a paragraph is not
  kept: the lines are joined. A metadata header (`Version: 1.2` over
  `Language: English`) becomes one line. Make it a list or a table, or end
  each line but the last with a backslash. Prose wrapped at 80 columns is
  fine to leave as it is.
- **Headings stop at level 3.** `####` and deeper become plain text: raise
  them, make them bold lines, or split the page if the depth means it holds
  several pages.
- **Links between pages** must be relative and end in `.md` to become page
  links: `../guide/intro` becomes `../guide/intro.md`, `/docs/guide/intro`
  (a site path) becomes the relative path, a link to a folder names its
  `readme.md`, `[[Page]]` and `[[Page|label]]` become `[Page](path/Page.md)`
  and `[label](path/Page.md)`. An anchor to another page (`other.md#setup`)
  is dropped: the link opens the page.
- Footnotes, definition lists, raw HTML (`<br>`, `<kbd>`, `<img>`,
  `<details>`, HTML tables), MDX components, shortcodes and Liquid tags,
  `{#id}` on headings, ```` ```math ```` fences, `\[ \]` delimiters and
  `:emoji:` shortcodes are all shown as literal text: each has a conversion
  in the reference.

What cannot be kept, say so rather than work around it: table column
alignment and image titles are dropped, text alignment has no Markdown form.

Keep the meaning, not the markup. When a construct has no faithful
equivalent (tabs of install commands per platform, a shortcode that built a
card grid), choose the structure a reader of the page needs (one `###`
section per tab, a list of links) and mention the choice in the report.

## 5. Verify

1. Run the checker again until nothing is left at the `breaks` level, and
   every `changes` entry is one the user accepted.
2. With `--cosmetic`, decide whether to normalise the rest now (`*` bullets
   to `-`, `_x_` to `*x*`, `~~~` to backticks, setext headings to `#`,
   reference links to inline, `<url>` to `[url](url)`). For a git sync it is
   worth it: the migration commit then holds every change, and Densho's
   first commit only adds the `id:` lines.
3. For a git sync, prove it before the real thing: connect a throwaway
   Densho space to a scratch branch of the migrated repository and read the
   first commit Densho pushes. Each file should gain its `id:` front matter,
   folders without a readme gain one, and nothing else should change. Any
   other difference is a construct the dialect does not read, and it will
   happen to the real space too.

## 6. Hand over

Report, in the user's language:

- what was converted, as counts per kind (42 callouts, 17 wiki links...),
- every lossy decision, with the files it touched,
- the renames, because links from outside the docs will need them,
- for a git sync: merge the branch, tell the team to pull, then connect the
  space to the folder. On macOS and Windows, a clone made before a
  case-only rename can keep the old spelling on disk and push it back: ask
  those people to commit their own work and re-clone.
