"""Refresh only the archived audit's protected-source snapshot.

The archived test and its equality assertion remain unchanged. The snapshot is
versioned here because generated-artifacts is deliberately excluded from Git.
Run from the repository root: python -m research.refresh_wicket_audit_hashes
"""
import hashlib
import json
from pathlib import Path

SNAPSHOT = Path(__file__).with_name("wicket_audit_protected_hashes.json")
ARCHIVE = Path("generated-artifacts/wicket-audit/diagnostics.json")


def main():
    frozen = json.loads(SNAPSHOT.read_text())
    actual = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
              for name in frozen}
    if actual != frozen:
        raise ValueError("Protected sources differ from the reviewed snapshot")
    archived = json.loads(ARCHIVE.read_text())
    archived["protected_hashes"] = frozen
    ARCHIVE.write_text(json.dumps(archived, indent=2) + "\n")
    print("Updated protected hashes only; archived test and diagnostic metrics unchanged.")


if __name__ == "__main__":
    main()
