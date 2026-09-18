#!/usr/bin/env python3
"""Lists what in a folder of Markdown will not survive Densho as it is.

Densho reads a folder as a tree of pages (a folder is a page whose text is
its readme.md, X.md is a page titled X) and rewrites every file it takes in
into its own dialect. Whatever that dialect cannot read is escaped, merged
or dropped, and with the git sync the damage is committed back to the
repository on the first cycle. Run this before importing or connecting, fix
what it reports, and run it again until nothing blocking is left.

Three levels:
  breaks    the content or the tree comes out wrong (escaped callouts,
            joined lines, a second page for one folder...)
  changes   Densho writes it back differently (a renamed file, a lost
            table alignment): decide whether that is acceptable
  cosmetic  Densho normalises it on its first write (`*` bullets become
            `-`...). Harmless; convert it too if you want the migration
            commit, not Densho's first one, to hold every change

Usage: check_densho_ready.py <folder> [--json] [--cosmetic]
Exit status: 1 when anything at the `breaks` level remains, else 0.
Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import unquote

# Folders the git sync owns or skips: never read as pages.
RESERVED_DIRS = {".git", ".trash", "assets", "synced-blocks"}
# Folders nobody wants imported.
SKIPPED_DIRS = {".git", "node_modules", ".obsidian", ".vitepress", ".docusaurus"}
# Callout types the ::: family renders.
CALLOUTS = {"info", "note", "success", "warning", "danger"}
OTHER_CONTAINERS = {"custom", "toggle", "details", "columns", "column", "pagebreak", "subpages"}
# Characters Densho replaces in a page title when it names the file back.
UNSAFE_NAME = re.compile(r'[\\/:*?"<>|]')
MAX_NAME = 80
# Inline HTML the escaper will show as text. Comments are fine.
HTML_TAG = re.compile(r"</?([A-Za-z][\w-]*)(?:\s[^<>]*)?/?>")
LINK = re.compile(r"(!?)\[([^\]]*)\]\(\s*<?([^()\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")


@dataclass
class Finding:
    level: str
    rule: str
    path: str
    line: int
    detail: str


def key(name: str) -> str:
    """How Densho compares names: case and accent encoding ignored."""
    return unicodedata.normalize("NFC", name).lower()


def page_name(file_name: str) -> str:
    return file_name[:-3] if file_name.lower().endswith(".md") else file_name


def sanitized(name: str) -> str:
    """The name Densho gives a file when it writes a page back."""
    cleaned = re.sub(r"\s+", " ", UNSAFE_NAME.sub(" ", name)).strip()[:MAX_NAME]
    return cleaned or "Untitled"


class Checker:
    def __init__(self, root: Path, cosmetic: bool):
        self.root = root
        self.cosmetic = cosmetic
        self.findings: list[Finding] = []
        self.md_files: list[Path] = []

    def add(self, level: str, rule: str, path: Path | str, line: int, detail: str) -> None:
        if level == "cosmetic" and not self.cosmetic:
            return
        rel = path if isinstance(path, str) else str(path.relative_to(self.root))
        self.findings.append(Finding(level, rule, rel or ".", line, detail))

    # ── Layout ─────────────────────────────────────────────────────────────

    def walk(self) -> None:
        for dirpath, dirnames, filenames in os.walk(self.root):
            here = Path(dirpath)
            dirnames[:] = sorted(d for d in dirnames if d not in SKIPPED_DIRS)
            self.check_folder(here, dirnames, sorted(filenames))
            for name in dirnames:
                if name in RESERVED_DIRS and self.holds_markdown(here / name):
                    self.add(
                        "breaks", "reserved-folder", here / name, 0,
                        f'a folder named "{name}" is never read as pages; '
                        "rename it if it holds documentation",
                    )
            dirnames[:] = [d for d in dirnames if d not in RESERVED_DIRS]
            for name in sorted(filenames):
                path = here / name
                if path.is_symlink() and name.lower().endswith((".md", ".mdx")):
                    self.add("breaks", "symlink", path, 0,
                             "a symbolic link is never read: copy the file instead")
                elif name.lower().endswith(".md"):
                    self.md_files.append(path)
                elif name.lower().endswith(".mdx"):
                    self.add("breaks", "mdx-file", path, 0,
                             "only .md files are pages: convert it to .md "
                             "(drop the imports, turn components into Markdown)")

    @staticmethod
    def holds_markdown(folder: Path) -> bool:
        return any(f.lower().endswith(".md") for _, _, files in os.walk(folder) for f in files)

    def check_folder(self, here: Path, dirs: list[str], files: list[str]) -> None:
        md = [f for f in files if f.lower().endswith(".md")]
        readmes = [f for f in md if f.lower() == "readme.md"]
        if len(readmes) > 1:
            self.add("breaks", "readme-twins", here, 0,
                     f"{' and '.join(readmes)} are one file for Densho (and for "
                     "macOS): keep one")
        if not readmes and here != self.root:
            index = [f for f in md if f.lower() in {"index.md", "_index.md"}]
            if index:
                self.add("changes", "index-not-readme", here / index[0], 0,
                         "a folder's own text lives in readme.md: rename it (and "
                         "the links to it), or it becomes a child page named "
                         f'"{page_name(index[0])}"')

        # Two entries that are the same name for Densho, macOS and Windows:
        # the first import makes two pages, and the sync renames them back
        # and forth. A folder and a file of the same name are two pages with
        # one title, one of which gets "(2)".
        seen: dict[str, str] = {}
        for entry in [d + "/" for d in dirs if d not in RESERVED_DIRS] + md:
            if entry.lower() == "readme.md":
                continue
            name = entry[:-1] if entry.endswith("/") else page_name(entry)
            k = key(name)
            if k in seen:
                self.add("breaks", "name-twins", here, 0,
                         f'"{seen[k]}" and "{entry}" are one name for Densho: '
                         "merge them or rename one")
            else:
                seen[k] = entry
            if sanitized(name) != name:
                self.add("changes", "unsafe-name", here / entry.rstrip("/"), 0,
                         f'Densho writes this page back as "{sanitized(name)}": '
                         "rename it now so links do not break later")

    # ── Content ────────────────────────────────────────────────────────────

    def check_files(self) -> None:
        for path in self.md_files:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                self.add("breaks", "encoding", path, 0, "not UTF-8: re-encode it")
                continue
            self.check_text(path, text)

    def check_text(self, path: Path, text: str) -> None:
        lines = text.split("\n")
        start = self.front_matter(path, lines)
        fence: str | None = None
        paragraph: list[tuple[int, str]] = []
        prev_blank = True
        containers: list[tuple[int, str]] = []  # (colons, kind) of open ::: blocks

        def flush() -> None:
            self.check_paragraph(path, paragraph)
            paragraph.clear()

        for i in range(start, len(lines)):
            raw = lines[i]
            n = i + 1
            stripped = raw.strip()
            opener = re.match(r"^\s{0,3}(`{3,}|~{3,})\s*([\w+-]*)", raw)
            if fence:
                if opener and opener.group(1)[0] == fence[0] and len(opener.group(1)) >= len(fence) and not opener.group(2):
                    fence = None
                continue
            if opener:
                flush()
                fence = opener.group(1)
                if fence.startswith("~"):
                    self.add("cosmetic", "tilde-fence", path, n, "becomes a ``` fence")
                if opener.group(2).lower() == "math":
                    self.add("breaks", "math-fence", path, n,
                             "a ```math fence shows as code: use $$ ... $$")
                continue
            if not stripped:
                flush()
                prev_blank = True
                continue
            if prev_blank and raw.startswith("    ") and not re.match(r"^\s*([-*+]|\d+[.)])\s", raw):
                self.add("cosmetic", "indented-code", path, n, "becomes a ``` fence")
            prev_blank = False
            fenceline = re.match(r"^(:{3,})\s*([\w-]*)", stripped)
            if fenceline and fenceline.group(2).lower() not in {"pagebreak", "subpages"}:
                colons, kind = len(fenceline.group(1)), fenceline.group(2).lower()
                if kind:
                    outer = next((c for c in reversed(containers) if c[1] not in {"columns", "column"}), None)
                    if outer and kind not in {"columns", "column"} and outer[0] <= colons:
                        self.add("breaks", "nested-container", path, n,
                                 f":::{kind} inside :::{outer[1]}: its closing ::: closes the "
                                 "outer block too, now or on Densho's next write; move it out")
                    containers.append((colons, kind))
                elif containers:
                    containers.pop()
            prose = re.sub(r"`[^`\n]*`", "``", raw)
            self.check_line(path, n, raw, prose, lines, i)
            if self.is_paragraph_line(stripped):
                paragraph.append((n, raw))
            else:
                flush()
        flush()
        if fence:
            self.add("breaks", "unclosed-fence", path, 0,
                     "a code fence is never closed: the rest of the file is code")

    def front_matter(self, path: Path, lines: list[str]) -> int:
        if not lines or lines[0].strip() != "---":
            self.first_heading(path, lines, 0)
            return 0
        for end in range(1, len(lines)):
            if lines[end].strip() == "---":
                head = lines[1:end]
                for number, line in enumerate(head, start=2):
                    owned = re.match(r"^(id|sort|order|space):", line)
                    if owned:
                        self.add("breaks", "front-matter-key", path, number,
                                 f'"{owned.group(1)}:" is Densho\'s own key and gets replaced: '
                                 "remove it or rename it (an order becomes an NN- prefix)")
                title = next((re.sub(r"^title:\s*", "", l).strip().strip("'\"")
                              for l in head if l.startswith("title:")), None)
                if title and key(title) != key(page_name(path.name)) and path.name.lower() != "readme.md":
                    self.add("changes", "front-matter-title", path, 1,
                             f'the page is titled after the file ("{page_name(path.name)}"), '
                             f'not after title: "{title}": rename the file if the '
                             "title should win")
                self.first_heading(path, lines, end + 1)
                return end + 1
        return 0

    def first_heading(self, path: Path, lines: list[str], start: int) -> None:
        for i in range(start, len(lines)):
            if not lines[i].strip():
                continue
            h1 = re.match(r"^#\s+(.+?)\s*#*\s*$", lines[i])
            name = path.parent.name if path.name.lower() == "readme.md" else page_name(path.name)
            if h1 and key(re.sub(r"^\d+-", "", name)) == key(h1.group(1).strip()):
                self.add("changes", "duplicate-title", path, i + 1,
                         "this heading repeats the page title, which Densho already "
                         "shows above the text: drop it")
            return

    @staticmethod
    def is_paragraph_line(stripped: str) -> bool:
        return not re.match(r"^(#{1,6}\s|[-*+]\s|\d+[.)]\s|>|\||:::|!!!|\?\?\?|<|\$\$|---|===)", stripped)

    def check_paragraph(self, path: Path, para: list[tuple[int, str]]) -> None:
        """Lines of one paragraph are joined into one: harmless for wrapped
        prose, a loss when each line is its own item."""
        if len(para) < 2:
            return
        texts = [t for _, t in para]
        if any(re.search(r"\{\{[<%]|\{%", t) or re.match(r"^:\s", t.strip()) for t in texts):
            return  # reported by the shortcode or definition-list rule
        broken = [t for t in texts[:-1] if t.endswith("\\") or t.endswith("  ")]
        if broken:
            if any(t.endswith("  ") and not t.endswith("\\") for t in texts[:-1]):
                self.add("cosmetic", "two-space-break", path, para[0][0],
                         "a two-space line break is rewritten as a trailing backslash")
            return
        key_value = sum(1 for t in texts if re.match(r"^\s*(\*\*)?[^\s:][^:]{0,40}:(\*\*)?\s+\S", t))
        short = all(len(t.strip()) < 50 for t in texts)
        if key_value == len(texts) or (short and len(texts) >= 3):
            self.add("breaks", "joined-lines", path, para[0][0],
                     f"these {len(texts)} lines become one line: make them a list "
                     "or a table, or end each line but the last with a backslash")

    def check_line(self, path: Path, n: int, raw: str, prose: str, lines: list[str], i: int) -> None:
        s = raw.strip()
        heading = re.match(r"^(#{1,6})\s", s)
        if heading and len(heading.group(1)) > 3:
            self.add("breaks", "deep-heading", path, n,
                     f"a level {len(heading.group(1))} heading becomes plain text: "
                     "use ### or a bold line, or split the page")
        if heading and re.search(r"\{#[\w-]+\}\s*$", s):
            self.add("breaks", "heading-id", path, n, "the {#id} is shown as text: remove it")
        if re.match(r"^(=+|-+)\s*$", s) and i > 0 and lines[i - 1].strip() and self.is_paragraph_line(lines[i - 1].strip()):
            self.add("cosmetic", "setext-heading", path, n, "becomes a # heading")
        if re.match(r"^>\s*\[!\w+\]", s):
            self.add("breaks", "alert-callout", path, n,
                     "a GitHub or Obsidian callout is shown as a quote with [!TYPE] "
                     "in it: use a ::: callout")
        if re.match(r"^(!!!|\?\?\?\+?)\s*\w+", s):
            self.add("breaks", "admonition", path, n,
                     "a MkDocs admonition is shown as text: use a ::: callout "
                     "(??? becomes :::toggle)")
        container = re.match(r"^:::+\s*([\w-]+)(.*)$", s)
        if container:
            kind, rest = container.group(1).lower(), container.group(2).strip()
            if kind not in CALLOUTS | OTHER_CONTAINERS:
                self.add("breaks", "unknown-container", path, n,
                         f":::{kind} is not a Densho block: use one of "
                         "info, note, success, warning, danger, custom, toggle")
            elif kind in CALLOUTS and rest:
                self.add("breaks", "callout-title", path, n,
                         f'the title "{rest}" after :::{kind} is dropped: '
                         "put it in bold on the first line inside")
        if re.search(r"<(details|summary)\b", prose, re.I):
            self.add("breaks", "html-details", path, n, "<details> is shown as text: use :::toggle Title")
        if re.search(r"\[\^[^\]]+\]", prose):
            self.add("breaks", "footnote", path, n,
                     "footnotes are shown as text: move the note into the sentence or a callout")
        for embed in re.finditer(r"(!?)\[\[([^\]]+)\]\]", prose):
            if embed.group(2).startswith(("synced-block:", "synced-blocks/")):
                continue
            self.add("breaks", "wiki-embed" if embed.group(1) else "wiki-link", path, n,
                     f"[[{embed.group(2)}]] is shown as text: write a relative "
                     "Markdown link to the .md file" if not embed.group(1) else
                     f"![[{embed.group(2)}]] is shown as text: write ![](relative/path)")
        if re.match(r"^\s*(import|export)\s.+\sfrom\s+['\"]", raw) or re.match(r"^\s*import\s+['\"]", raw):
            self.add("breaks", "mdx-import", path, n, "an MDX import line is shown as text: remove it")
        if re.search(r"\+\+[A-Za-z0-9]+(?:\+[A-Za-z0-9]+)+\+\+", prose):
            self.add("breaks", "mkdocs-keys", path, n,
                     "++ctrl+c++ is underline in Densho: write `Ctrl+C` in backticks")
        if re.search(r"\{\{[<%]|\{%", prose):
            self.add("breaks", "shortcode", path, n,
                     "a Hugo shortcode or Liquid tag is shown as text: write what it produced")
        if re.search(r"\\\[|\\\(", prose):
            self.add("breaks", "latex-delimiters", path, n, r"\[ \] and \( \) are shown as text: use $$ and $")
        if re.match(r"^:\s+\S", s) and i > 0 and lines[i - 1].strip():
            self.add("breaks", "definition-list", path, n,
                     "a definition list becomes one line: write **Term**: definition")
        tags_here: set[str] = set()
        for tag in HTML_TAG.finditer(prose):
            name = tag.group(1)
            if name.lower() in {"details", "summary"} or name.lower() in tags_here:
                continue
            tags_here.add(name.lower())
            if name[0].isupper():
                self.add("breaks", "jsx-component", path, n,
                         f"<{name}> is an MDX component, shown as text: turn it into Markdown")
            else:
                self.add("breaks", "raw-html", path, n,
                         f"<{name}> is shown as text: use the Markdown equivalent "
                         "(see the conversion reference), or ```htmlrender if it must render")
        for m in re.finditer(r"(?<![\w:`/]):([a-z][a-z0-9_+-]*):(?![\w:])", prose):
            if "_" in m.group(1) or m.group(1) in {"smile", "warning", "tada", "rocket", "bulb", "memo", "x", "heavy_check_mark"}:
                self.add("breaks", "emoji-shortcode", path, n,
                         f":{m.group(1)}: is shown as text: write the emoji itself")
        if re.search(r"^\s*\|?\s*:?-{3,}:\s*\|", s) or re.search(r"\|\s*:-{3,}", s):
            self.add("changes", "table-alignment", path, n, "column alignment is lost on import")
        if re.match(r"^\s*\*\s", raw):
            self.add("cosmetic", "star-bullet", path, n, "becomes a - bullet")
        if re.match(r"^\s*\d+\)\s", raw):
            self.add("cosmetic", "paren-list", path, n, "becomes 1.")
        if re.search(r"(?<![\w*_])_[^_\s][^_]*_(?![\w_])|__[^_]+__", prose):
            self.add("cosmetic", "underscore-emphasis", path, n, "becomes * or **")
        if re.search(r"<https?://[^>]+>", prose):
            self.add("cosmetic", "autolink", path, n, "becomes [url](url)")
        if re.match(r"^\s*\[[^\]]+\]:\s+\S", raw) or re.search(r"\]\[[^\]]*\]", prose):
            self.add("cosmetic", "reference-link", path, n, "becomes an inline link")
        for link in LINK.finditer(prose):
            self.check_link(path, n, link.group(1) == "!", link.group(3), raw)

    def check_link(self, path: Path, n: int, image: bool, dest: str, raw: str) -> None:
        if re.match(r"^[a-z][a-z0-9+.-]*:", dest, re.I) or dest.startswith("#"):
            return
        target, _, anchor = dest.partition("#")
        target = unquote(target)
        if image and re.search(r'\]\([^)]*\s+"', raw):
            self.add("changes", "image-title", path, n, 'an image title ("...") is dropped')
        if "|" in target:
            return
        if target.startswith("/"):
            bare = target.lstrip("/")
            candidates = [self.root / bare, self.root.parent / bare]
            # /docs/guide/intro on a site whose docs live in docs/
            if bare.split("/", 1)[0] == self.root.name and "/" in bare:
                candidates.append(self.root / bare.split("/", 1)[1])
            base = "an absolute site link"
        else:
            candidates = [path.parent / target]
            base = "this link"
        resolved = next((c for c in candidates if c.exists()), None)
        if resolved is None:
            for c in candidates:
                for ext in (".md", ".mdx"):
                    if Path(str(c) + ext).exists():
                        resolved = Path(str(c) + ext)
            if resolved is not None and resolved.suffix == ".md":
                self.add("breaks", "link-without-md", path, n,
                         f'{base} ("{dest}") names a page without .md: Densho only '
                         "turns relative links ending in .md into page links; write "
                         f'"{os.path.relpath(resolved, path.parent)}"')
                return
            if resolved is None:
                if image or Path(target).suffix and Path(target).suffix.lower() != ".md":
                    self.add("breaks", "missing-file", path, n,
                             f'"{dest}" is not in the folder: the file cannot be imported')
                else:
                    self.add("changes", "dead-link", path, n, f'"{dest}" points at nothing in the folder')
                return
        if target.startswith("/"):
            self.add("breaks", "absolute-link", path, n,
                     f'"{dest}" only works on the old site: write it relative, '
                     f'"{os.path.relpath(resolved, path.parent)}"')
            return
        if resolved.is_dir():
            readme = next((resolved / f for f in os.listdir(resolved) if f.lower() == "readme.md"), None)
            if readme or any(f.lower() in {"index.md", "_index.md"} for f in os.listdir(resolved)):
                self.add("breaks", "folder-link", path, n,
                         f'"{dest}" names a folder: link its readme.md so it becomes a page link')
            return
        if resolved.suffix.lower() == ".mdx":
            self.add("breaks", "link-to-mdx", path, n, f'"{dest}" names an .mdx file: link the converted .md')
        elif resolved.suffix.lower() == ".md" and anchor:
            self.add("changes", "cross-page-anchor", path, n,
                     f'the "#{anchor}" part is dropped: the link opens the page, not the section')

    # ── Report ─────────────────────────────────────────────────────────────

    def check_git_index(self) -> None:
        """Case twins live in the git index even where the disk cannot hold
        them: on macOS and Windows `Developer/` and `developer/` are one
        folder on disk and two in the repository, which is how a sync ends
        up renaming a folder back and forth."""
        try:
            out = subprocess.run(
                ["git", "-C", str(self.root), "ls-files", "-z", "--full-name", "."],
                capture_output=True, check=True,
            ).stdout.decode("utf-8", "replace")
            prefix = subprocess.run(
                ["git", "-C", str(self.root), "rev-parse", "--show-prefix"],
                capture_output=True, check=True, text=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return
        seen: dict[str, str] = {}
        reported: set[str] = set()
        for full in filter(None, out.split("\0")):
            rel = full[len(prefix):] if full.startswith(prefix) else full
            parts = rel.split("/")
            # Every ancestor folder, then the file itself
            for depth in range(1, len(parts) + 1):
                spelled = "/".join(parts[:depth])
                k = key(spelled)
                other = seen.setdefault(k, spelled)
                if other != spelled and k not in reported:
                    reported.add(k)
                    self.add("breaks", "name-twins", ".", 0,
                             f'the repository holds both "{other}" and "{spelled}": '
                             "one path for Densho, macOS and Windows; merge them with "
                             "git mv (through a temporary name on a case-insensitive disk)")

    def run(self) -> list[Finding]:
        self.walk()
        self.check_git_index()
        self.check_files()
        order = {"breaks": 0, "changes": 1, "cosmetic": 2}
        self.findings.sort(key=lambda f: (order[f.level], f.rule, f.path, f.line))
        return self.findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folder", type=Path, help="the folder Densho will read (the synced folder, or the one you will zip)")
    parser.add_argument("--json", action="store_true", help="print the findings as JSON")
    parser.add_argument("--cosmetic", action="store_true", help="also list what Densho merely normalises")
    args = parser.parse_args()
    root = args.folder.resolve()
    if not root.is_dir():
        print(f"not a folder: {root}", file=sys.stderr)
        return 2

    checker = Checker(root, args.cosmetic)
    findings = checker.run()
    blocking = sum(1 for f in findings if f.level == "breaks")

    if args.json:
        print(json.dumps({
            "folder": str(root),
            "pages": len(checker.md_files),
            "summary": {lvl: sum(1 for f in findings if f.level == lvl) for lvl in ("breaks", "changes", "cosmetic")},
            "findings": [asdict(f) for f in findings],
        }, indent=2, ensure_ascii=False))
        return 1 if blocking else 0

    print(f"{root}: {len(checker.md_files)} Markdown file(s)")
    if not findings:
        print("Nothing left that Densho would mangle.")
        return 0
    current = None
    for f in findings:
        if (f.level, f.rule) != current:
            current = (f.level, f.rule)
            count = sum(1 for g in findings if (g.level, g.rule) == current)
            print(f"\n[{f.level}] {f.rule} ({count})")
        where = f"{f.path}:{f.line}" if f.line else f.path
        print(f"  {where}  {f.detail}")
    totals = {lvl: sum(1 for f in findings if f.level == lvl) for lvl in ("breaks", "changes", "cosmetic")}
    print(f"\n{totals['breaks']} breaks, {totals['changes']} changes"
          + (f", {totals['cosmetic']} cosmetic" if args.cosmetic else "")
          + (" - fix the breaks and run again." if blocking else " - nothing blocking."))
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
