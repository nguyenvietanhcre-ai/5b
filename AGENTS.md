# Mầm Toán — project instructions

## Read at the start of every session
Read docs/PROJECT_MEMORY.md, docs/SESSION_LOG.md and README.md before changing the project.

## Persistent user instructions
- All project source, documentation, deliverables and task scratch files belong under F:\ChatGPT Math Project. Use work/ for disposable files.
- Use Python backend, Git/GitHub source control and Docker/Compose packaging.
- Preserve the approved playful green/orange frontend unless asked to change it.
- At the end of EVERY work session or completed task: update PROJECT_MEMORY.md when decisions change, and append SESSION_LOG.md with changes, actual checks and remaining work.
- These files provide durable project memory. Do not claim global model memory guarantees recall across chats.
- Propose repeatable workflows as skills; obtain explicit user confirmation BEFORE creating or installing a skill. Record suggestions in docs/SKILL_CANDIDATES.md; do not create SKILL.md without approval.
- Distinguish local Git commits, GitHub pushes and deployments. Never claim Docker or GitHub CI checks passed unless actually run.
- Do not invent admission policies, recorded videos, live class links or real account protection.

## Development
- Run: python -m backend --host 127.0.0.1 --port 8765
- Tests: python -m unittest discover -s tests -v
- JS syntax: node --check frontend/app.js
- Docker: docker compose up --build
- Only explicit frontend assets may be public; never expose repository root, internal docs or .git.
- User profiles, uploads and classes are demo-only. Real authentication, databases and teacher tools are future work.
