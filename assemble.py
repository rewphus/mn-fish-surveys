#!/usr/bin/env python3
"""Substitutes the embedded font and dataset into template.html to produce
the final, self-contained artifact.html."""

with open("template.html") as f:
    template = f.read()

with open("font.b64") as f:
    font_b64 = f.read().strip()

with open("app_data.json") as f:
    data_json = f.read()

with open("mn_places.json") as f:
    places_json = f.read()

# Prevent the embedded JSON from accidentally closing the <script> tag early
# if any string value contains "</". \/ is a valid JSON escape for /.
data_json_safe = data_json.replace("</", "<\\/")
places_json_safe = places_json.replace("</", "<\\/")

out = (
    template.replace("__FONT_BASE64__", font_b64)
    .replace("__DATA_JSON__", data_json_safe)
    .replace("__PLACES_JSON__", places_json_safe)
)

with open("index.html", "w") as f:
    f.write(out)

import os
print(f"index.html written: {os.path.getsize('index.html') / 1024 / 1024:.2f} MB")
