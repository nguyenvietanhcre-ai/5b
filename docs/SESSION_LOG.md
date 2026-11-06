# Session log

## 2026-11-06 — Initial demo
- Approved concept and original sample content. Created playful green/orange HTML/CSS/JS demo, lessons, quizzes, game and demo student dashboard.
- Browser checked full-score practice/exam, zero-score blank submission, lesson progress after reload, game completion and narrow-screen overflow. Screenshot: demo-preview.jpg.

## 2026-11-06 — Python / GitHub / Docker foundation
- User requested Python, GitHub, Docker; durable memory after each task; confirmation before creating skills.
- Moved public UI into frontend/. Added dependency-free Python server, health endpoint and exact fraction/decimal grading. HTTP frontend calls Python; offline file viewing retains client grading.
- Added Dockerfile, Compose, ignore rules, Python/JS/Docker CI and Windows launcher.
- Added AGENTS.md, PROJECT_MEMORY.md and skill candidates. No skill created.
- Local: 10 Python tests passed; JS syntax passed; running Python health and full-score grade API passed at http://127.0.0.1:8766.
- Docker not found; no local container run claimed. Browser recheck of this migration was blocked by a Windows app helper startup error; earlier demo visual checks remain valid only for the original UI.
- GitHub connected; user selected public repo nguyenvietanhcre-ai/5b. Repo confirmed initially empty. Upload in progress; record resulting commit/CI outcome below.
- Next: inspect GitHub CI after upload, confirm proposed skills, then real authentication/database/teacher workflows.

### Final result of GitHub attempt
- Created local Git commit 5749a47 and configured origin https://github.com/nguyenvietanhcre-ai/5b.git.
- Connector write denied with HTTP 403 Resource not accessible by integration. CLI push could not authenticate; no remote changes. No GitHub Actions runs.
- User action needed: enable content/workflow write access for the GitHub connection, or sign into Git on the machine; then push main and inspect CI. No passwords/tokens requested in chat.
- Python demo remains available at http://127.0.0.1:8766. Local Docker unavailable.

## 2026-11-06 — GitHub source upload completed
- User explicitly requested uploading local source to GitHub.
- User completed Git Credential Manager browser authentication.
- Pushed main to origin; local and remote matched e3949a6b371d92e547390a0285d492608c271672.
- GitHub Actions Python and Docker checks passed: https://github.com/nguyenvietanhcre-ai/5b/actions/runs/42186397763.
- Updated README and durable project memory to remove the resolved CLI authentication blocker; these documentation updates are committed and pushed as a follow-up.
- No skills created; previous skill proposals still await user confirmation.
