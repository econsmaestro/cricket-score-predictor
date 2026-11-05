"""Public-source downloads, isolated from the online prediction path."""
import hashlib
import json
from pathlib import Path

import requests

ARCHIVES = (
    "tests_male_json.zip", "tests_female_json.zip", "ipl_json.zip",
    "bbl_json.zip", "wbb_json.zip", "psl_json.zip", "cpl_json.zip", "wpl_json.zip",
)
ATTRIBUTION = "Derived from Cricsheet (https://cricsheet.org/), Open Data Commons Attribution License 1.0"


def download_archive(name, root=Path("generated-artifacts/fielding/sources")):
    if name not in ARCHIVES:
        raise ValueError("Select an explicitly supported Cricsheet archive")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    destination = root / name
    temporary = root / (name + ".part")
    if not destination.exists():
        response = requests.get(f"https://cricsheet.org/downloads/{name}", timeout=(15, 90), stream=True)
        response.raise_for_status()
        try:
            size = 0
            with temporary.open("wb") as stream:
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > 200_000_000:
                        raise ValueError("Archive exceeds the offline ingestion size limit")
                    stream.write(chunk)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
            response.close()
    with destination.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    (root / (name + ".manifest.json")).write_text(json.dumps({
        "source": f"https://cricsheet.org/downloads/{name}", "sha256": digest,
        "attribution": ATTRIBUTION, "license": "https://cricsheet.org/licensing/",
    }, indent=2))
    return destination
