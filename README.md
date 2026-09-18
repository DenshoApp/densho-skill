# Densho Skills

Agent skills that teach AI assistants to work with
[Densho](https://densho.app), the self-hosted knowledge base.

> Knowledge worth passing on.

| Skill | For |
| --- | --- |
| [`densho`](skills/densho/SKILL.md) | Working inside a workspace through its MCP server: search the wiki, read a page, draft or update one, comment, organise, without wrecking what the team wrote. |
| [`densho-migrate`](skills/densho-migrate/SKILL.md) | Converting existing documentation (GitHub, GitLab, Obsidian, MkDocs, Docusaurus, VitePress, Hugo, Jekyll, GitBook, Notion) to the Densho dialect and folder layout, before Import Markdown or the git sync takes it over. |

## densho

`SKILL.md` is the judgment layer: when to act, in which order, and what has
consequences for the people on the other side. It deliberately does **not**
restate the Densho Markdown syntax.

The syntax already lives in the product. The MCP server exposes a
`get_markdown_reference` tool that returns the exact dialect the connected
instance renders, and the skill tells the assistant to call it before writing.
One source of truth, versioned with the instance, so this skill can never
drift from what the editor actually understands.

Scope is the editor: spaces, pages, their organisation and comments. Kanban
boards and chat are out.

**Requirements.**

- A Densho instance whose license includes the **MCP** feature.
- The instance's MCP endpoint connected in the AI client, authorized by the
  user. The assistant's reach is exactly that user's: private spaces stay
  private, and the write tools only appear if write access was granted.

## densho-migrate

Densho rewrites every file it takes in into its own dialect. What it cannot
read (a GitHub `> [!NOTE]`, a MkDocs admonition, a wiki link, a metadata
header written as separate lines, a folder spelled two ways) is escaped,
merged or duplicated rather than refused, and with the git sync that result
is committed back to the repository on the first cycle. This skill converts
first, on a branch, so the first commit Densho pushes only adds page ids.

It works on files, before Densho ever sees them, and needs no Densho
connection. Unlike `densho`, it carries the syntax itself, since there is no
instance to ask yet:

- `SKILL.md`: the method (target, inventory, layout, syntax, verification,
  hand-over) and the decisions that belong to the user.
- `references/conversions.md`: each construct, what Densho does with it, and
  what to write instead, per source tool.
- `scripts/check_densho_ready.py`: lists what in a folder will not survive
  Densho, at three levels (`breaks`, `changes`, `cosmetic`). Python 3,
  standard library only. Inside a git repository it also reads the index,
  where two spellings of one folder can live on a case-insensitive disk.

```bash
python3 skills/densho-migrate/scripts/check_densho_ready.py path/to/docs            # exit 1 while something breaks
python3 skills/densho-migrate/scripts/check_densho_ready.py path/to/docs --cosmetic # also what Densho only normalises
python3 skills/densho-migrate/scripts/check_densho_ready.py path/to/docs --json
```

## Install

**Claude Code.** Each skill is a folder: clone the repository once and link
the ones you want into your skills directory.

```bash
git clone https://github.com/DenshoApp/densho-skill ~/densho-skill
ln -s ~/densho-skill/skills/densho ~/.claude/skills/densho
ln -s ~/densho-skill/skills/densho-migrate ~/.claude/skills/densho-migrate
```

`densho` is a single file, so copying it works too:

```bash
mkdir -p ~/.claude/skills/densho
curl -o ~/.claude/skills/densho/SKILL.md \
  https://raw.githubusercontent.com/DenshoApp/densho-skill/main/skills/densho/SKILL.md
```

`densho-migrate` needs its whole folder, the script and the reference
included. Project-wide instead of personal: put the skill folders in
`.claude/skills/` inside the repository, and they ship with the project.

**Other clients.** The skills are plain Markdown with a small YAML header.
Point the client at a skill folder if it supports them; otherwise paste the
body of `SKILL.md` into its custom-instruction field.

## Contributing

The skills are written to be read by a model, so they stay in English, short,
and free of anything the tool descriptions already say. If you find an
instruction that assistants keep getting wrong in practice, that is exactly
what belongs here.

Syntax rules for `densho` do not: send those to `docs/markdown-format.md` in
the main repository, which the instance's own reference follows. The
conversions in `densho-migrate` follow that same file and the behaviour of
Densho's import and git sync: when Densho learns a construct, update the
reference and drop the checker rule; when a migration keeps tripping on
something, add both.
