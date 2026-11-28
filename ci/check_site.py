#!/usr/bin/env python3
"""Checks for the static reader site. Standard library plus `node --check`.

Fails when:
  * paid subscriber notes are written into a public page again;
  * an inline script has a syntax error;
  * a script looks up an element id that the page does not have;
  * an id is used twice in one page;
  * a local link, image or #anchor points at nothing;
  * the API base URL is not https.

Usage: python3 ci/check_site.py [site directory]
"""
import html.parser
import os
import re
import subprocess
import sys
import tempfile

# Keys and text of the subscriber notes that used to ship inside index.html.
# Those notes now come only from the API after sign-in.
PAID_MARKERS = [
    "proFindings",
    "proOverview",
    "Subscriber interrogation notes for",
]

ID_LOOKUP = re.compile(
    r"""getElementById\(\s*["']([^"']+)["']\s*\)"""
    r"""|querySelector(?:All)?\(\s*["']#([A-Za-z][\w-]*)["']\s*\)"""
)
API_BASE = re.compile(r"""API_BASE(?:_URL)?\s*=\s*["']([^"']*)["']""")


class Page(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.refs = []  # (attribute, value, line)
        self.scripts = []  # (start line, code)
        self._script = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.append((a["id"], self.getpos()[0]))
        for name in ("href", "src"):
            if a.get(name):
                self.refs.append((name, a[name], self.getpos()[0]))
        if tag == "script" and not a.get("src") and a.get("type", "text/javascript") in (
            "text/javascript", "module", "application/javascript"
        ):
            self._script = (self.getpos()[0], [])

    def handle_data(self, data):
        if self._script is not None:
            self._script[1].append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._script is not None:
            self.scripts.append((self._script[0], "".join(self._script[1])))
            self._script = None


def check_page(root, name, errors):
    path = os.path.join(root, name)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    page = Page()
    page.feed(text)
    page.close()

    for marker in PAID_MARKERS:
        if marker in text:
            line = text[: text.index(marker)].count("\n") + 1
            errors.append(f"{name}:{line}: paid subscriber content marker {marker!r} is in a public page")

    seen = {}
    for ident, line in page.ids:
        if ident in seen:
            errors.append(f"{name}:{line}: id {ident!r} is also used on line {seen[ident]}")
        seen.setdefault(ident, line)

    for attr, value, line in page.refs:
        if re.match(r"^(?:[a-z][a-z0-9+.-]*:|//)", value, re.I):
            continue  # external URL, mailto:, data:, javascript:
        target, _, anchor = value.partition("#")
        target = target.split("?")[0]
        if target:
            if not os.path.exists(os.path.normpath(os.path.join(root, target))):
                errors.append(f"{name}:{line}: {attr}={value!r} points to a file that doesn't exist")
        elif anchor and anchor not in seen:
            errors.append(f"{name}:{line}: {attr}={value!r} points to an id that doesn't exist")

    for start, code in page.scripts:
        if not code.strip():
            continue
        for m in ID_LOOKUP.finditer(code):
            ident = m.group(1) or m.group(2)
            if ident not in seen:
                line = start + code[: m.start()].count("\n")
                errors.append(f"{name}:{line}: script looks up id {ident!r}, which the page doesn't have")
        for m in API_BASE.finditer(code):
            if not m.group(1).startswith("https://"):
                line = start + code[: m.start()].count("\n")
                errors.append(f"{name}:{line}: API base URL {m.group(1)!r} is not https")
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as tmp:
            tmp.write(code)
        try:
            result = subprocess.run(["node", "--check", tmp.name], capture_output=True, text=True)
        finally:
            os.unlink(tmp.name)
        if result.returncode != 0:
            lines = result.stderr.strip().splitlines()
            where = re.search(r":(\d+)$", lines[0]) if lines else None
            line = start + int(where.group(1)) - 1 if where else start
            message = next((l.strip() for l in lines if "Error" in l), "see node --check output")
            errors.append(f"{name}:{line}: inline script has a syntax error: {message}")
    return len(page.scripts)


def main(argv):
    root = argv[1] if len(argv) > 1 else "."
    pages = sorted(n for n in os.listdir(root) if n.endswith(".html"))
    if "index.html" not in pages:
        print("index.html not found", file=sys.stderr)
        return 1
    errors = []
    for name in pages:
        scripts = check_page(root, name, errors)
        print(f"checked {name} ({scripts} inline script{'s' if scripts != 1 else ''})")
    for e in errors:
        print(f"::error::{e}" if os.environ.get("GITHUB_ACTIONS") else f"error: {e}")
    if errors:
        print(f"{len(errors)} problem(s) found")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
