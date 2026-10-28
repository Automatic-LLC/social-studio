# Social Studio

Automated, original-content posting for Instagram and Facebook accounts. First account:
[@ur_dailydog](https://www.instagram.com/ur_dailydog) (comedy dogs).

- `social_studio/`: the code (`publisher.py` posts what's due, `meta.py` talks to Meta, `captions.py` checks
  captions, `store.py` is the Supabase database and media bucket).
- `accounts/`: one file per account (handle, ids, post times, caption rules, hashtags).
- `config.yaml`: shared settings and the kill switch (`paused`).
- `docs/`: the public site (privacy policy, data deletion, contest rules), served by GitHub Pages.
- `supabase/migrations/`: the database tables.
- `.github/workflows/`: the publisher (every 15 min), a daily queue check, tests.

Setup: [SETUP.md](SETUP.md). Status and plan: [ROADMAP.md](ROADMAP.md).

```
py -m pip install -r requirements.txt
py -m social_studio doctor
py -m pytest -q
```
