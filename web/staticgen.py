import json
import shutil
from pathlib import Path
from lxml import etree


Path("./static").mkdir()

files = {
    "js": [],
    "xml": [],
}

for file in list(Path("./app").glob("**/*")):
    if not file.is_file():
        continue
    match file.suffix:
        case ".js":
            files["js"].append(file)
        case ".xml":
            files["xml"].append(file)
        case _:
            (Path("./static") / file.parents[0]).mkdir(parents=True, exist_ok=True)
            shutil.copy(file, Path("./static") / file)

importmap = {
    "imports": {}
}

Path("./static/js").mkdir()
for file in files["js"]:
    p = file.parent.relative_to("./app") / file.name
    importmap["imports"][f"@{str(p.with_suffix(''))}"] = "./js/" + str(p)

    (Path("./static/js") / p.parents[0]).mkdir(parents=True, exist_ok=True)
    shutil.copy(file, Path("./static/js") / p)

xml_out = etree.Element("templates")
xmlparser = etree.XMLParser(remove_comments=True)
for file in files["xml"]:
    tree = etree.parse(file, parser=xmlparser)
    for child in tree.getroot():
        xml_out.append(child)

(etree.ElementTree(xml_out)).write("./static/templates.xml", xml_declaration=True)

with open("./static/index.html", "w", encoding="utf-8") as f:
    f.write(f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>test</title>

    <script type="importmap">{json.dumps(importmap)}</script>
    <script type="module" src="./js/root.js"></script>
  </head>
  <body>
  </body>
</html>
""")
