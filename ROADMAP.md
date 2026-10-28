# Social Studio roadmap and status

The plan: "ur_dailydog Growth & Automation Plan" (Oct 26, 2026). This file records what changed from that plan and
where the build stands. Update it whenever something changes.

## Status (2026-10-28, evening)

- **Phase 1 (foundation): code done, waiting on Aaron's setup** (SETUP.md A-E). Done when `test-post` puts one
  image on @ur_dailydog.
- **Phase 2 (publisher): core done** (GitHub Actions every 15 min, Instagram image/carousel/Reel/Story, Facebook
  Reels, reserve fills empty slots, phone alerts, daily queue check). Still to build: the batch preview page with
  Kill/Swap buttons (today: `py -m social_studio kill <id>`). Done when a queued post goes out with the laptop shut.
- **Phase 3 (content, no GPU): Reel maker in** (`social_studio/edit/reels.py`: 9:16, meme text on top, credit,
  end card, voiceover and music mixing; `sources/pexels.py`; `batch.py`: plan file → renders → `preview.html` →
  `--go` queues into free daily slots, extras to the reserve). Still to build: caption drafting by an LLM,
  carousels (Pillow slides), a voice for voiceovers (Kokoro or Piper, both run on a CPU).
- Phases 4-6: not started.

## Decisions (Aaron, 2026-10-28) and what they changed

- **Name: Social Studio**, built for more than one account. Every account is a file in `accounts/`; every row in
  the database has an `account`. First account: `ur_dailydog`.
- **Start building now.** The order is changed so the account benefits sooner: publisher → real clips + Pexels +
  captions → contest → AI video last.
- **Repo public**, so GitHub Pages hosts the site (`docs/`) and Actions minutes are free.
- **No VPS, no R2.** GitHub Actions runs the publisher (free, about 5-15 min timing slack, fine for this).
  Supabase holds the database *and* the media (public `media` bucket, files deleted after posting), so there's no
  Cloudflare account or card on file. Cost so far: $0/month.
- **Meta system-user token, expiry Never**, instead of 60-day tokens and a weekly refresh job.
- **No trending audio** (the API can't use Instagram's music library): on-screen text, voiceover, or royalty-free
  music when it fits.
- **Contest screening gets a human check** (Aaron agreed with the safety concerns): the AI screen still runs, plus
  the Friday draw lands in the preview with a phone alert so a person sees it before Sunday. Screening also rejects
  faces of people who didn't agree, addresses, house numbers and plates, not only kids' faces.
- **No email.** Winners are told by the tag on the winning post (Instagram notifies them); anything else goes
  through the account's DM inbox by hand. Cooldown matches on Instagram handle.
- **AI label: fine.** Every AI post carries it (`is_ai`), and Aaron thinks it may even draw clicks.
- Supabase: Social Studio gets its **own** project. The project connected to Claude belongs to another business.

## Phases

1. **Foundation**: Meta app + system-user token, Supabase project, site with privacy and data-deletion pages,
   `doctor` and `test-post`. *(code done)*
2. **Publisher**: `social_studio/publisher.py`, `.github/workflows/publish.yml` and `daily.yml`. *(core done;
   preview page next)*
3. **Content, no GPU**: ffmpeg Reel templates (9:16 crop, POV text overlay, end card, optional voiceover/music),
   Pexels source with credit capture, caption writer (an LLM behind `captions.check`; local Ollama on the desktop,
   or Claude in a session until then), `batch` command that turns a folder of clips into queued posts 2-3 weeks out.
4. **Dog of the Week**: submission page in `docs/ur_dailydog/` (uploads to a private Supabase bucket, consent
   checkboxes), `submissions` table, screening, random draw with 90-day cooldown, winner carousel, preview check.
5. **AI generation (desktop GPU)**: ComfyUI (FLUX stills, Wan 2.2 video), vision QA gate, AI label. Higgsfield
   only for hero clips if local quality isn't enough.
6. **Insights + more platforms**: daily metrics pull, weekly plan leans into what worked, YouTube Shorts, manual
   TikTok, then TikTok's API audit (needs a domain).
7. **AI City building**: Social Studio on a Downtown lot in the Trading repo's City (each building is one AI
   project). It only shows things: queue days, next post, last post status, contest entries; it never touches the
   trading floors.

## Open items

- Check the AI-label parameter name (`config.yaml: ai_label_param`) against Meta's Content Publishing docs before
  the first AI post.
- GitHub turns off scheduled workflows in a repo with no commits for 60 days (it emails first). Normal work keeps
  it on; the City building should also warn if no post went out in 2 days.
- Honorable mentions and the 90-day cooldown: default no (Aaron hasn't decided).
- Facebook Reels must be 3-90 s; Reels longer than 90 s will need `to_facebook: false` (the Reel builder will set it).
