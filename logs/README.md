# Diagnostic logs

Upload GameNative capture logs here for review of the SD865 / Adreno 650 memory-pressure investigation.

## Recommended files

- `driver-and-runtime-report*.txt`
- `capture-metadata*.txt`
- Relevant DXVK / Turnip logs covering the same capture session
- Optional: a short `SESSION_NOTES.md` with game, driver profile, resolution/settings, and whether the run reproduced `VK_ERROR_OUT_OF_DEVICE_MEMORY`

## Capture guidance

- Keep logs from a single run together and use a clear filename prefix, for example `2026-10-16-ff7remake-memory-audit-`.
- Include the full log around allocation failures, sparse-bind retries/failures, heap/budget reporting, and the start/end of capture where possible.
- Do not include account tokens, passwords, private keys, or unrelated personal data.
- Preserve the original logs; do not trim the surrounding lines around errors.

This folder is for diagnostic artifacts only. Uploading files here does not automatically trigger a build or change driver code.