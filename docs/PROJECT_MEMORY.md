# Project memory
Updated: 2026-11-06 (Asia/Saigon).

## Confirmed objective
Vietnamese learning website for grade-5 students, Kết nối tri thức plus advanced topics and grade-6 entrance preparation.
Named target schools: Cầu Giấy, Amsterdam, Chuyên Ngoại Ngữ, Lương Thế Vinh, Nguyễn Tất Thành.
Interpret Chuyên Ngoại Ngữ provisionally as THCS Ngoại ngữ. Target admission year has not been confirmed.
Use past Ams papers as advanced reference only; verify current official notices before advertising admissions.

## Product
Public visitors read information; the full product will require accounts for learning, downloads and homework.
Self-study videos/readings plus live Zoom/Meet classes.
Playful, rich illustrations. Style reference: https://bigtreeland.vn/. Use original branding/assets.
Demo name: Mầm Toán, not yet final branding.
User approved the plan and requested a demo.

## Content
Original sample materials: comparing decimals; successive percentage changes; five-question 15-minute mini test; decimal-sorting game.
Do not label as official school papers. SGK lesson/page mapping needs review.
Profiles/results remain browser localStorage. Homework only records a filename; no files sent to a teacher.
Video scripts only; no recorded video or real class links.

## User's standing requirements
Python backend, GitHub repository/workflows, Docker packaging.
All files under F:\ChatGPT Math Project.
Save decisions and work history after every task/session.
Propose possible skills and get confirmation before creating them.

## Architecture
backend/: dependency-free Python 3.12+ demo HTTP server and exact-arithmetic grading.
frontend/: existing original HTML/CSS/JS UI.
API: GET /api/health; POST /api/grade.
HTTP UI uses Python grading. Direct frontend/index.html retains offline client grading for review.
Dockerfile + compose.yaml package the demo; no auth/database yet.
.github/workflows/ci.yml runs Python tests, JS syntax and Docker smoke checks after GitHub push.
Server exposes explicit frontend files only, not internal project files.

## Environment / external state
GitHub destination confirmed by user: https://github.com/nguyenvietanhcre-ai/5b (public). Connected GitHub access verified; repository initially empty. Initial upload in progress.
Docker executable not found during inspection; local container build/run unverified.
System python is an uninstalled Microsoft Store alias.
Bundled Python 3.12.14 is usable for local verification; start-demo.ps1 locates it without committing a user-specific absolute path.
