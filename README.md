# Densho Skill

An agent skill that teaches AI assistants how to work inside a
[Densho](https://densho.app) workspace: search the wiki, read a page, draft or
update one, and comment, without wrecking what the team wrote.

> Knowledge worth passing on.

## What it is, and what it is not

`SKILL.md` is the judgment layer: when to act, in which order, and what has
consequences for the people on the other side. It deliberately does **not**
restate the Densho Markdown syntax.

The syntax already lives in the product. The MCP server exposes a
`get_markdown_reference` tool that returns the exact dialect the connected
instance renders, and the skill tells the assistant to call it before writing.
One source of truth, versioned with the instance, so this repository can never
drift from what the editor actually understands.

Scope is the editor: spaces, pages and comments. Kanban boards are out.

## Requirements

- A Densho instance whose license includes the **MCP** feature.
- The instance's MCP endpoint connected in the AI client, authorized by the
  user. The assistant's reach is exactly that user's: private spaces stay
  private, and the write tools only appear if write access was granted.

## Install

**Claude Code.** Copy the skill into your skills directory:

```bash
mkdir -p ~/.claude/skills/densho
curl -o ~/.claude/skills/densho/SKILL.md \
  https://raw.githubusercontent.com/DenshoApp/densho-skill/main/SKILL.md
```

Project-wide instead of personal: put it in `.claude/skills/densho/SKILL.md`
inside the repository, and it ships with the project.

**Other clients.** The file is plain Markdown with a small YAML header. Paste
its body into whatever custom-instruction field the client offers, or point the
client at it if it supports skill folders.

## Contributing

The skill is written to be read by a model, so it stays in English, short, and
free of anything the tool descriptions already say. If you find an instruction
that assistants keep getting wrong in practice, that is exactly what belongs
here. Syntax rules do not: send those to `docs/markdown-format.md` in the main
repository, which the instance's own reference follows.
