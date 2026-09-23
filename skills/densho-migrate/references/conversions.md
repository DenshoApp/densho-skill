# Conversions to the Densho dialect

Each section: what the source writes, what Densho does with it as is, and
what to write instead. Densho's own syntax is summed up at the end.

Contents:

1. Callouts and admonitions
2. Collapsible blocks
3. Line breaks and metadata headers
4. Headings
5. Links between pages
6. Images, embeds and files
7. Raw HTML
8. Footnotes, definition lists, abbreviations
9. Math and diagrams
10. Tool-specific leftovers (MDX, MkDocs, Hugo, Jekyll, GitBook, Notion)
11. Front matter
12. Losses to report, not to fix
13. The Densho dialect at a glance

## 1. Callouts and admonitions

Densho has five callout types, `info`, `note`, `success`, `warning`,
`danger`, plus `:::custom <emoji>`. A callout has no title line: whatever
follows the type is dropped, so a title goes in bold on the first line
inside.

```markdown
:::warning
**Before you upgrade**

Back up the database first.
:::
```

| Source | Type in Densho |
| --- | --- |
| GitHub `> [!NOTE]` / `[!TIP]` / `[!IMPORTANT]` / `[!WARNING]` / `[!CAUTION]` | note / success / info / warning / danger |
| Obsidian `> [!note]`, `abstract`, `summary`, `tldr`, `info`, `todo` | note or info |
| Obsidian `tip`, `hint`, `important`, `success`, `check`, `done` | success (tip, hint) or info (important) |
| Obsidian `question`, `help`, `faq` | info |
| Obsidian `warning`, `caution`, `attention` | warning |
| Obsidian `failure`, `fail`, `missing`, `danger`, `error`, `bug` | danger |
| Obsidian `example`, `quote`, `cite` | a plain `>` quote (quote, cite) or info (example) |
| MkDocs `!!! note "Title"` (body indented 4 spaces) | same families as Obsidian; un-indent the body |
| Docusaurus `:::note`, `:::tip`, `:::info`, `:::caution`, `:::warning`, `:::danger` (title as `:::tip Title` or `:::tip[Title]`) | note, success, info, warning, warning, danger |
| VitePress `::: tip`, `::: warning`, `::: danger`, `::: info` | success, warning, danger, info |
| GitBook `{% hint style="info\|success\|warning\|danger" %}` | same name |
| Hugo `{{< hint info >}}`, `{{< notice warning >}}` | same name |
| Jekyll `{% include note.html content="..." %}` and similar includes | the matching type |
| Notion `<aside>` with an emoji | `:::custom <that emoji>` |

An admonition whose body is only a title (`!!! note "Remember to save"`)
becomes a callout holding that sentence.

## 2. Collapsible blocks

`:::toggle Title` ... `:::` is a collapsible block; the title stays on the
opening line.

| Source | Densho |
| --- | --- |
| `<details><summary>Why</summary> ... </details>` | `:::toggle Why` ... `:::` |
| MkDocs `??? note "Why"`, `???+ note "Why"` | `:::toggle Why` |
| Obsidian `> [!faq]- Why` (the `-` or `+` makes it foldable) | `:::toggle Why` |
| VitePress `::: details Why` | `:::toggle Why` (`:::details Why` also works) |

**A callout inside a toggle** (or a toggle inside a toggle) needs a longer
fence on the outer block. Every `:::` fence closes the block opened by the
shortest fence, so with two `:::` fences the callout's closing `:::` closes
the toggle too. Write `::::toggle Why` ... `::::` around the callout's
`:::info` ... `:::`: Densho keeps the longer fence when it writes the page
back, as it does for columns and flashcards. Instances from before that
change write `:::toggle` back and break the nesting on the next round trip:
there, put the callout before or after the toggle instead.

## 3. Line breaks and metadata headers

A single newline inside a paragraph is not kept: the two lines become one.
Prose wrapped at a fixed width reads the same once joined, so leave it. What
breaks is text whose lines are items:

```markdown
Version: 1.2
Original language: English
Status: draft
```

comes back as `Version: 1.2 Original language: English Status: draft`.
Write a list (or a two-column table when there are many fields):

```markdown
- **Version**: 1.2
- **Original language**: English
- **Status**: draft
```

When the line layout itself matters (an address, a poem, a signature), end
every line but the last with a backslash:

```markdown
Ascension team\
Lyon, France
```

Two trailing spaces also work but are invisible and stripped by many
editors; Densho rewrites them as the backslash. `<br>` is shown as text.

## 4. Headings

Headings stop at level 3; `####` and deeper become plain paragraphs, and
`{#custom-id}` after a heading is shown as text.

- A page that needs level 4 usually holds several pages: split it, one page
  per `##` section, under a folder. That is also what makes the Densho tree
  useful.
- Otherwise raise every level by one when the page has no level 1 (Densho
  shows the page title above the text, so the body rarely needs `#`), or
  turn the deepest level into a bold line.
- Remove `{#id}`. Links to that anchor from other pages lose the anchor
  anyway (see 5).
- Setext headings (`Title` over `=====`) are read fine and rewritten as `#`.

## 5. Links between pages

Densho turns a link into a page link when it is **relative** and ends in
**`.md`**, and the target file is part of the imported folder. Anything else
stays a plain link, which in Densho points nowhere.

| Source | Write |
| --- | --- |
| `[Intro](../guide/intro)` (no extension, MkDocs, Docusaurus, Hugo) | `[Intro](../guide/intro.md)` |
| `[Intro](/docs/guide/intro)` (a site path) | the relative path from this file, with `.md` |
| `[Guide](../guide/)` (a folder) | `[Guide](../guide/readme.md)` |
| `[[Intro]]` (Obsidian, by file name anywhere in the vault) | `[Intro](relative/path/Intro.md)`: find the file by name, ignoring case; ask when two files share it |
| `[[Intro\|the intro]]` | `[the intro](relative/path/Intro.md)` |
| `[[Intro#Setup]]`, `[Intro](intro.md#setup)` | the page link without the section: Densho drops the anchor |
| `{{< ref "intro.md" >}}`, `{% link docs/intro.md %}`, `{{ site.baseurl }}/intro` | the relative path |
| Docusaurus `[Intro](intro-id)` (by doc id) | find the file whose front matter says `id: intro-id` |
| Notion `Intro%201a2b3c4d.md` (id suffixes) | strip the id from file names and links alike |

A name with spaces is written percent-encoded (`Getting%20started.md`);
the angle-bracket form (`<Getting started.md>`) is not recognised. A link to the same page's heading
(`#setup`) is kept as written.

After renaming or moving files, update every link that pointed at them. The
checker reports `link-without-md`, `absolute-link`, `folder-link` and
`dead-link` for what is left.

## 6. Images, embeds and files

Images and files linked with a relative path are imported as attachments;
with the git sync they stay where they are in the repository. The file must
be inside the imported folder: a link that climbs out of it (`../../static/
img/logo.png`, Docusaurus `@site/static/...` or `/img/...`) cannot be read,
so copy the file into the folder and point at the copy.

| Source | Densho |
| --- | --- |
| `![alt](img.png "title")` | `![alt](img.png)` (the title is dropped) |
| `![[diagram.png]]`, `![[diagram.png\|300]]` (Obsidian) | `![](diagram.png)`, `![\|width=300](diagram.png)` with the relative path |
| `![alt](img.png =300x)` and other size suffixes | `![alt\|width=300](img.png)` |
| `<img src="a.png" width="300" align="right">` | `![\|width=300 align=right](a.png)` |
| `<p align="center"><img ...></p>` | the image alone: centred is the default |
| `![[Other note]]` (embedding a whole note) | a link to it; copy the text only if the user wants it duplicated |
| `<video src>`, `<audio src>` | `[Video](file.mp4)`, `[Audio](file.mp3)` on a line of their own |
| a PDF | `[PDF](file.pdf)` on its own line shows a viewer; inside a sentence it is a link |
| one page of a PDF | `[PDF](file.pdf#page=3)` on its own line shows that page alone (1-based) |
| `<iframe src="https://www.youtube.com/embed/...">` | `[YouTube](https://www.youtube.com/embed/...)` on its own line, keeping the embed URL; `[Vimeo](...)` the same |
| Hugo `{{< figure src="a.png" caption="..." >}}` | the image, then the caption in italics on the next paragraph |

Do not name a documentation folder `assets`: the git sync keeps binaries
there and never reads it as pages. Binaries inside an `assets/` folder are
fine.

## 7. Raw HTML

Tags are escaped and shown as text (comments `<!-- ... -->` are kept and
hidden, which suits linter directives). Use the Markdown form:

| HTML | Densho |
| --- | --- |
| `<b>`, `<strong>` / `<i>`, `<em>` | `**x**` / `*x*` |
| `<code>` | `` `x` `` |
| `<kbd>Ctrl</kbd>+<kbd>C</kbd>` | `` `Ctrl+C` `` |
| `<sub>` / `<sup>` | `~x~` / `^x^` |
| `<mark>` | `==x==` |
| `<u>`, `<ins>` | `++x++` |
| `<s>`, `<del>` | `~~x~~` |
| `<a href="...">` | `[text](...)` (and section 5 for internal targets) |
| `<br>` in a paragraph | a backslash at the end of the line |
| `<br>` in a table cell | a cell holds one line: separate with `;`, or move the content out of the table |
| `<hr>` | `---` |
| a simple `<table>` | a GFM table |
| `<div>`, `<span>`, `<p>`, `<center>` used for layout | drop the tags, keep the text |
| anything meant to render or run (a widget, a styled card, a form) | a fenced ` ```htmlrender ` block, self-contained: it runs in a sandbox |

## 8. Footnotes, definition lists, abbreviations

- **Footnotes** (`text[^1]` with `[^1]: note`) are shown as text. Fold a
  short note into its sentence, in parentheses. For long or many notes,
  write `(note 1)` in the text and end the page with a `### Notes` numbered
  list.
- **Definition lists** (`Term` over `: definition`) become one line. Write
  `- **Term**: definition`, or a two-column table.
- **Abbreviation definitions** (MkDocs `*[HTML]: HyperText Markup Language`)
  are shown as text: remove them, or expand the first use in the text.

## 9. Math and diagrams

- Block math is `$$ ... $$` (on its own lines, or `$$x^2$$` on one line).
  A ```` ```math ```` fence shows as code, and `\[ ... \]` as text.
- Inline math is `$x^2$`, with no space just inside the dollars. `\( ... \)`
  is shown as text.
- ```` ```mermaid ```` renders. PlantUML, Graphviz and other diagram fences
  stay code listings: keep them as code, or redraw simple ones in Mermaid
  when the user wants them rendered.

## 10. Tool-specific leftovers

**MDX (Docusaurus).** Rename to `.md`, then:

- delete `import ... from '...'` and `export ...` lines;
- `<Tabs>` with `<TabItem value="npm" label="npm">`: one `### npm` section
  per tab (or one `:::toggle npm` each when the tabs are alternatives few
  readers need);
- `<Admonition type="tip">` : a callout (section 1);
- `<CodeBlock language="js">`: a fenced block;
- `{/* comment */}`: an HTML comment or nothing;
- a component with no Markdown meaning (`<DocCardList />`): drop it, or
  `:::subpages` when it listed the child pages.

**MkDocs Material.**

- `=== "Tab"` content tabs: `### Tab` sections, un-indented;
- `--8<-- "file.md"` snippet includes: paste the included text;
- `++ctrl+alt+del++` (pymdownx.keys) is **underline** in Densho: write
  `` `Ctrl+Alt+Del` ``;
- `^^text^^` (pymdownx.caret insert): `++text++`;
- `{ .class }` attribute lists and `[TOC]` markers: remove;
- the `nav:` of `mkdocs.yml`: `NN-` prefixes on file and folder names.

**Hugo.** Shortcodes are shown as text: `hint`/`notice` to callouts,
`figure` to an image, `ref`/`relref` to relative links, `highlight` to a
fence, `tabs` as for MDX. `_index.md` is the folder's readme. `weight:` in
front matter becomes an `NN-` prefix.

**Jekyll / Liquid.** `{% highlight js %}` to a fence, `{% include %}` to
what it rendered, `{% raw %}`/`{% endraw %}` markers removed, `{{ ... }}`
variables replaced by their value.

**GitBook.** `{% hint %}` to a callout, `{% tabs %}` as for MDX,
`{% embed url="..." %}` to an embed link (section 6), `{% content-ref %}` to
a page link. `SUMMARY.md` gives the order (`NN-` prefixes); it then becomes
a page of its own, so remove it or keep it as the root readme.

**Notion export.** Strip the 32-character ids from file and folder names
and from links, turn `<aside>` into callouts, and give each exported
database (a CSV next to a folder) a GFM table or a link, as the user
prefers.

**Emoji shortcodes** (`:white_check_mark:`, `:warning:`): write the emoji
itself, ✅ ⚠️. Densho shows the shortcode as text.

## 11. Front matter

The block between `---` lines at the top of a file.

- The git sync keeps keys it does not own in the file, hidden from the
  page. Import Markdown drops them.
- **`id:` is Densho's**: it holds the page's identity. Docusaurus writes
  `id: intro` in every doc; Densho reads it as an unknown page id and
  replaces it. Remove it (after resolving the links that used it, see 5), or
  rename it (`doc_id:`) if another tool still needs it.
- **`sort:`, `order:` and `space:`** are Densho's too (the order of a
  folder's pages, in its readme). A site generator's `order: 3` must become
  an `NN-` prefix.
- **`title:`** does not name the page, the file does. When they differ and
  the title is the one readers know, rename the file (and its links).
- `sidebar_position:`, `weight:`, `nav_order:`: fold them into `NN-`
  prefixes, then drop them if nothing else reads them.

## 12. Losses to report, not to fix

- Table column alignment (`:---`, `---:`): dropped.
- Image titles: dropped.
- Text alignment and colours: no Markdown form.
- Anchors in links to other pages: dropped, the link opens the page.
- Soft line breaks in wrapped prose: joined, which reads the same.

## 13. The Densho dialect at a glance

- Headings `#` to `###`; bold, italic, `~~strike~~`, `==highlight==`,
  `++underline++`, `~sub~`, `^sup^`; bold, italic and links may cover
  `` `code` ``.
- A hard line break is a backslash at the end of the line.
- GFM tables, task lists `- [ ]`, quotes, `---` dividers, fenced code with a
  language, ```` ```mermaid ````, ```` ```htmlrender ````.
- `$inline$` and `$$block$$` math.
- Callouts `:::info|note|success|warning|danger` and `:::custom 🔥`,
  `:::toggle Title`, `:::subpages`, `:::pagebreak`, columns as `::::columns`
  wrapping one `:::column` per column, flashcards as `::::flashcard`
  wrapping `:::front` then `:::back` (a question and its answer, turned over
  by the reader).
- Images `![alt|width=500 height=300 align=left](src)`; `[Video](src)`,
  `[Audio](src)`, `[PDF](src)`, `[YouTube](url)` on their own line become
  players; `[PDF](src#page=3)` shows that one page of the document. Those
  links take the same size and alignment after a pipe,
  `[Video|width=480 align=center](src)`, and `::::flashcard` and
  `:::subpages` take them on their opening line; the audio player takes a
  width only.
- `<!-- comments -->` are kept, hidden.
- Chips (`[@Name](mention:id)`, `[@Name](profile:id)` for a profile card on
  its own line, `[label](page:id)`, `[file](element:pageId/attachmentId)`
  for a file of another page, `[text](status:color)`) need ids from a
  Densho instance: a migration writes relative `.md` links instead, which
  the import turns into page links.
