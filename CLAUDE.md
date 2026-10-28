# Social Studio: start here

Automated posting for Aaron's social accounts (first: @ur_dailydog, a comedy dog page). Read `ROADMAP.md` (status
and decisions) and, for setup questions, `SETUP.md`. The Trading repo's AI City will show this as one building.

Rules that never bend:
- Tokens and keys live in `.env` / `C:\Trading\SocialStudio.env` on Aaron's PCs and in GitHub Actions secrets: never
  print, log or commit them; never ask for them in chat. The repo is public.
- Tests never call Meta or Supabase for real (fakes in `tests/conftest.py`). Only Aaron runs `test-post` / `add`.
- Original or licensed content only: no downloading and reuploading other people's posts. Submissions need the
  license checkbox; Pexels clips need our own overlay and credit.
- Every AI-made post sets `is_ai` (Meta's AI label). No fake rescue or sad stories.
- No post goes out unless `qa_passed` and `caption_ok`; `paused: true` in `config.yaml` stops everything.
- All Meta calls stay in `social_studio/meta.py`.
- Supabase: use only the "Superbase - Social Studio" connector (project slxgihuyzscnxoftxnqa). The plain "Superbase"
  connector is another business's project: never touch it.

Git: work on `main` only, never create a branch (Aaron, 2026-10-28). Commit and push straight to `main`.

Tests: `py -m pytest -q` (Linux: `python -m pytest -q`). When something changes, update `ROADMAP.md`.
