---
name: GitHub transfer integrity
description: Preserve file contents when Git transport authentication requires a connector-based upload.
---

If Git push authentication fails but the GitHub integration can write, publish through the integration without forcing branch updates. Verify every uploaded blob and the final tree against local Git object hashes.

**Why:** Large base64 file transfers through shell callback output lost prefixes despite the truncation flag not reporting it. A direct text file read and per-blob hash comparison preserved the complete content. The incomplete upload was corrected before delivery.

**How to apply:** Use direct file reads for connector uploads, not long stdout payloads. Treat equal file counts or a successful GitHub response as insufficient verification; fetch the branch and compare its tree to the local snapshot.
