# Latest Handoff

Updated: 2026-04-13 02:49 KST

## GitHub

- Private remote: `https://github.com/millim1983/openharness_mm.git`
- Branch: `web-mvp-rag`
- Latest pushed commit: `45f7c3b feat(proposal): add announcement agent folder upload flow`
- Public `origin` and original `upstream` are not used for this private development flow.

## Server Environment Variables

Use these on the company Ubuntu server:

```bash
export OPENHARNESS_CONFIG_DIR=/home/회사계정/.openharness
export OPENHARNESS_DATA_DIR=/home/회사계정/.openharness/data
export OPENHARNESS_WEB_HOST=0.0.0.0
export OPENHARNESS_WEB_PORT=8014
export OPENHARNESS_PROPOSAL_OUTPUT_DIR=/data/openharness/announcements
export OPENHARNESS_RAG_EMBEDDING_PROFILE=openai-compatible
```

Meanings:

- `OPENHARNESS_CONFIG_DIR`: settings, credentials, project context, and feedback logs.
- `OPENHARNESS_DATA_DIR`: local RAG/VectorDB data.
- `OPENHARNESS_WEB_HOST=0.0.0.0`: allow access from the company network or externally routed IP.
- `OPENHARNESS_WEB_PORT=8014`: web UI port.
- `OPENHARNESS_PROPOSAL_OUTPUT_DIR`: root directory where the project program creates announcement folders and output files.
- `OPENHARNESS_RAG_EMBEDDING_PROFILE`: embedding profile used by RAG indexing/search.

## Folder And Output Behavior

The project program can create folders and output files on the Ubuntu server.

Required condition:

- The Linux user running OpenHarness must have write permission to `OPENHARNESS_PROPOSAL_OUTPUT_DIR`.

Current announcement-agent behavior:

- User uploads a folder/file set from the web UI.
- Program finds the PDF notice file identified by `공고`.
- Program analyzes and RAG-indexes only that PDF notice.
- HWP, Excel, PPT, forms, manuals, and regulations are not parsed at this stage.
- Program creates a new announcement folder under `OPENHARNESS_PROPOSAL_OUTPUT_DIR`.
- Program saves the uploaded file set into that generated folder.
- Program creates `총괄장.xlsx` and `첨부파일목록.json` inside the generated folder.
- Program updates `공고리스트.json` and regenerates `공고리스트_yyyymmdd.xlsx` under `OPENHARNESS_PROPOSAL_OUTPUT_DIR`.

Important distinction:

- If files are uploaded through a browser, the server receives file bytes and saves them to the server output directory.
- The server cannot directly create folders or move files inside the user's original local PC folder chosen by the browser.
- If a company shared drive is mounted on the Ubuntu server, the program can create folders and move files there.
- A future watched-folder mode can support true server-side file movement from an intake folder into the generated announcement folder.

## Network Notes

To open the web UI on the company network:

- Run the web server with `OPENHARNESS_WEB_HOST=0.0.0.0`.
- Open `OPENHARNESS_WEB_PORT` in Ubuntu firewall, router/firewall, and cloud/security gateway if present.
- For external access, route the fixed public IP and external port to the Ubuntu server IP and `OPENHARNESS_WEB_PORT`.

Security note:

- Do not expose this MVP directly to the public internet without an auth layer or VPN/reverse proxy access control.
