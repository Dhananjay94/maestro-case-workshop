"""Builds ONE self-contained HTML file from WorkshopKit/Site (CSS and JS inlined).
Participants double-click it: no server, no install, no internet needed.
Usage: python build_single_site.py"""
import os
import re

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SITE = os.path.join(ROOT, "WorkshopKit", "Site")
OUT = os.path.join(ROOT, "WorkshopKit", "Motor_Claims_Workshop_Guide.html")


def read(*parts):
    with open(os.path.join(SITE, *parts), encoding="utf-8") as f:
        return f.read()


html = read("index.html")
css = read("css", "style.css")
scripts = [read("js", "data.js"), read("js", "app.js")]

for s in scripts:
    if "</script" in s.lower():
        raise SystemExit("a script contains </script>; cannot inline it safely")

html = html.replace('<link rel="stylesheet" href="css/style.css">', "<style>\n" + css + "\n</style>")
html = re.sub(r'<script src="js/data\.js"></script>\s*<script src="js/app\.js"></script>',
              lambda m: "<script>\n" + scripts[0] + "\n</script>\n<script>\n" + scripts[1] + "\n</script>", html)

if 'href="css/' in html or 'src="js/' in html:
    raise SystemExit("an external reference is left in the page")

with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write(html)
print(f"{os.path.relpath(OUT, ROOT)}: {os.path.getsize(OUT)//1024} KB, single file, no external files")
