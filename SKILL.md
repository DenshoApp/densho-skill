---
name: densho
description: Read and write pages in a Densho workspace through its MCP server. Use when the user asks to look something up in their wiki or documentation, draft or update a page, answer from what the team has written down, or leave feedback on a page. Covers pages, spaces, comments and the Densho Markdown dialect.
---

# Densho

Densho is a self-hosted knowledge base. A workspace holds **spaces**, each space
holds a tree of **pages**, and every page is a live collaborative document that
people may be editing at the same moment you are.

You reach it through the MCP server the user connected. Your access is exactly
theirs: a tool returning nothing usually means that space is not theirs to read,
not that the workspace is empty.

## The one rule about writing

**`update_page` replaces the entire body.** It is not an append. Writing without
reading first destroys whatever was there.

Recent instances enforce it: replacing content requires `expectedVersion`, the
token `get_page` returns. If the page changed since you read it, or the id is
wrong, the write is refused rather than silently applied. Read, merge, write:

1. `get_page` gives you `{ version, title, content }`
2. build the **complete** new body from that content
3. `update_page` with `content` and `expectedVersion: <version>`

If it comes back saying the page changed, re-read and redo the merge. Never
retry with the old version, and never work around the guard by dropping content
you did not read.

Older instances have no such token: `get_page` returns one Markdown document
with **the title prepended as an `# H1`**, which the body does not contain.
Feeding that straight back into `update_page` writes the title into the body and
the page then shows it twice. Strip that first heading before writing, and take
the same care with the rest: nothing there stops a bad write, so read the page
immediately before writing it and keep everything you are not deliberately
changing.

## Before you touch anything

- **Search before creating.** `search_pages` first. A wiki dies of duplicates,
  and the page you are about to write often exists under another title.
- **Call `get_markdown_reference` once per session** before authoring any page
  body. It returns the exact dialect this instance renders, from the instance
  itself, so it is never out of date. Do not guess the syntax from memory and do
  not assume GitHub-flavoured Markdown. If the tool is not offered, the instance
  predates it: keep to the constraints under "What will not work" below, and
  point the user at **Guide > Editor > "Markdown in and out"** in their own
  workspace for the full syntax.
- **Prefer commenting over editing** on a page you were not asked to change.
  `add_comment` puts your remark next to the text and notifies the author, which
  is the polite move on someone else's work.
- **Find where a page belongs** with `list_pages` before creating one. A wiki is
  a tree, and a page dropped at the root of a space is a page nobody finds. Pass
  `parentPageId`.
- **Write in the language of the pages around you**, not your own default. A
  workspace is often written in one language throughout, and a page in another
  one reads as an intruder.

## The tools

**Reading.** `list_spaces` (the spaces the user belongs to), `list_pages`
(a space's page tree as a flat list with parents), `search_pages` (full text,
optionally scoped to a space, at most 20 matches and no pagination, so refine
the query rather than take the list for the whole truth), `get_page` (title and
body as Markdown, plus the version token), `list_comments` (threads and their
resolution state).

**Writing.** `create_page` (in a space, optionally under a parent, optionally
with a body), `update_page` (title and/or full body), `add_comment` (a new
thread, or a reply with `parentCommentId`), `resolve_comment`.

Pages are also exposed as `densho://page/{id}` resources, so a client can attach
one directly.

Not every instance offers all of them. Write tools only exist if the user
granted write access when authorizing, and an older instance may lack the
comment listing, the resolution tool and the Markdown reference. Work with what
the client actually shows you, and say so rather than describing an edit you
cannot perform.

## Writing a page people will read

Structure it like documentation, not like a chat answer. Headings that say what
the section is about, short paragraphs, and lists where the content is a list.

- Use `:::info`, `:::warning` and the other callouts for what genuinely
  interrupts the reader. Three callouts in a row read as none.
- Use `:::toggle` for detail that most readers skip, not to hide the answer.
- Use `:::subpages` for an index of child pages rather than a hand written list
  of links, which goes stale the day someone adds a page.
- Prefer a table to a paragraph enumerating pairs of things.

Everything the editor supports round-trips through Markdown, so what you write
is what the person sees, and what they later export. The round trip normalises
as it goes: `$$maths$$` comes back on three lines, blocks gain blank lines
between them. Reading back something shaped slightly differently from what you
sent is normal and not a sign that anything failed.

## What will not work

- **Raw HTML tags** are escaped and shown as text. A fenced ` ```htmlrender `
  block is the way to render HTML, and it must be self contained: no network,
  no external assets.
- **GitHub callouts** (`> [!NOTE]`) are not part of the dialect: the brackets are
  escaped and the reader sees `\[!NOTE\]` inside a plain quote. Use a callout.
- **Footnotes** are worse than useless here. `text[^1]` with its `[^1]: note`
  definition comes out as `[^1](note)`, a link pointing at nothing. Write the
  aside inline or in a callout.
- **A ` ```math ` fence does not render.** Block maths is `$$ ... $$`.
- **You cannot upload anything.** There is no file or image tool, so never write
  a Markdown image pointing at a local path or a file you claim to have added.
  An image already in the page keeps working: leave its link untouched when you
  rewrite the body.
- **Never invent chip identifiers.** Mentions, page links and synced blocks
  encode real ids (`[@Name](mention:<userId>)`, `[label](page:<pageId>)`,
  `![[synced-blocks/...]]`). A made up id renders as a dead chip. Use a real id
  you obtained from a tool, or write a plain link.

## Things that have consequences for the team

- A page edited through you shows up **instantly** in the editor of anyone with
  it open, under their cursor. Rewriting a long page while someone works on it
  is disruptive even when it is technically safe.
- Editing a page marked **Verified** sends it back to "Ready to verify", which
  puts work on an admin's plate. Say so when you do it.
- Comments notify people. Do not open a thread for something you can fix in
  passing, and do not resolve a thread you did not address.

## Reporting back

Give the user the page title and where it lives, not raw ids. Say plainly what
you changed: a full body replacement is worth naming as such, and if you merged
your text into an existing page, say what you kept.
