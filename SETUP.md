# Social Studio setup: Aaron's checklist

Tick each box as you go. Runs from the desktop **and** the ThinkPad; no GPU needed until the AI-video phase.
**Never paste a secret into a chat with Claude** (Meta token, Supabase *secret* key, Pexels key). They go in your
password manager, the `.env` file on each PC and GitHub secrets only. Safe to paste: the ID numbers `doctor` prints,
the Supabase Project URL, the publishable key.

---

## ✅ Done (Oct 28)

- [x] Repo renamed to `Automatic-LLC/social-studio` and made public
- [x] Website live: https://automatic-llc.github.io/social-studio/privacy.html and `/data-deletion.html`
- [x] Supabase project `social-studio` created; tables `posts`, `post_log` and the public `media` bucket set up
      (Claude, through the "Superbase - Social Studio" connector)
- [x] ntfy app installed and a topic picked

---

## 1. Save the Supabase values (2 min) — now

- [ ] Supabase → social-studio project → **Project Settings → API Keys** → copy the **secret** key (`sb_secret_...`)
      into your password manager. That is `SUPABASE_KEY`.
- [ ] `SUPABASE_URL` is `https://slxgihuyzscnxoftxnqa.supabase.co` (not secret).

## 2. GitHub secrets (3 min) — now

github.com/Automatic-LLC/social-studio → Settings → Secrets and variables → Actions → **Secrets** tab →
New repository secret:

- [ ] `SUPABASE_URL`
- [ ] `SUPABASE_KEY`
- [ ] `NTFY_TOPIC` (your ntfy topic name)
- [ ] `PEXELS_KEY` (after step 4)
- [ ] Don't add `PUBLISHER_ON` yet (step 7).

## 3. Each PC: install and first check (15 min per PC) — now, on both PCs

- [ ] Python from python.org (tick **Add to PATH**). Check: `py --version`
- [ ] Git from git-scm.com. Check: `git --version`
- [ ] ffmpeg: in PowerShell `winget install Gyan.FFmpeg`, close and reopen PowerShell. Check: `ffmpeg -version`
- [ ] Get the code:
      ```
      cd C:\
      git clone https://github.com/Automatic-LLC/social-studio.git SocialStudio
      ```
- [ ] Secrets file: copy `C:\SocialStudio\.env.example` to `C:\SocialStudio\.env` (or save it as
      `C:\Trading\SocialStudio.env`) and fill in `SUPABASE_URL`, `SUPABASE_KEY`, `NTFY_TOPIC` (and `PEXELS_KEY`,
      `META_TOKEN` when you have them). Notepad is fine. Same file on both PCs.
- [ ] Double-click `C:\SocialStudio\setup.bat`. It installs everything and runs `doctor`, which should show
      **OK Supabase: posts table reachable**. The Meta lines stay empty until step 6.
- [ ] From now on, double-click `pull.bat` before working on a PC.

## 4. Pexels key (2 min) — now

- [ ] pexels.com/api → sign up → copy the API key → `.env` on both PCs as `PEXELS_KEY=...`, and the GitHub secret.

## 5. Content to start with — anytime

- [ ] In Google Drive make `SocialStudio\week1\` and put dog clips there that you own or have written permission
      for (phone videos are perfect). Either PC can then run the batch.
- [ ] Send Claude 2-3 phone screenshots of the profile and your best posts, plus any joke ideas. Claude drafts the
      first week's plan (on-screen text and captions).

## 6. Meta (30-45 min) — tonight

1. - [ ] **Check the link.** business.facebook.com → Settings → Accounts → Instagram accounts: @ur_dailydog is there
         and connected to the dog Facebook Page.
2. - [ ] **Developer account.** developers.facebook.com → Get started → log in with the Facebook account that runs
         the Page → verify your phone.
3. - [ ] **Create the app.** My Apps → Create app → use case **Other** → type **Business** → name `Social Studio` →
         connect it to the business portfolio that owns the Page.
4. - [ ] **App settings → Basic:**
         - Privacy Policy URL: `https://automatic-llc.github.io/social-studio/privacy.html`
         - User data deletion → Data deletion instructions URL:
           `https://automatic-llc.github.io/social-studio/data-deletion.html`
         - Category: e.g. Entertainment → **Save changes**
5. - [ ] **Add products** (left menu → Add product): **Instagram** → "API setup with Facebook login", and
         **Facebook Login for Business**.
6. - [ ] **System user.** business.facebook.com → Settings → Users → **System users** → Add → name
         `social-studio-bot`, role **Admin**. Then **Assign assets**:
         - Apps → Social Studio → full control
         - Pages → the dog Page → full control
         - Instagram accounts → @ur_dailydog → full control
7. - [ ] **Token.** On the system user → Generate new token → app **Social Studio** → expiration **Never** → tick:
         `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights`, `instagram_manage_comments`,
         `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `business_management`
         → Generate → **copy it into your password manager right away** (shown once). That is `META_TOKEN`.
8. - [ ] **Go Live.** App dashboard → App Mode: Development → **Live**.
9. - [ ] Put `META_TOKEN=...` in `.env` on both PCs, and add it as a GitHub secret.

## 7. First post and switch on (15 min) — tonight, one PC

- [ ] In `C:\SocialStudio`: `py -m social_studio doctor`. It prints your **fb_page_id** and **ig_user_id**: paste
      the two numbers to Claude (Claude commits them), then `pull.bat`.
- [ ] `doctor` again → ends with **all good** and shows your quota ("used 0 of 50").
- [ ] **Test post** (stays on the page unless you delete it in the app):
      ```
      py -m social_studio test-post --account ur_dailydog --file C:\path\to\dog.jpg --caption "Monday mood 🐶" --yes
      ```
- [ ] GitHub → Settings → Secrets and variables → Actions → **Variables** tab → `PUBLISHER_ON` = `true`
- [ ] GitHub → **Actions** tab → **publish** → Run workflow → it goes green.
- [ ] `py -m social_studio profile --account ur_dailydog` → paste the report to Claude (no secrets in it).
- [ ] **Hands-off test:** queue one post 30 min ahead (Central time), close the laptop, check the page later:
      ```
      py -m social_studio add --account ur_dailydog --kind image --file dog2.jpg --caption "Caption that passes the rules 😂 Does yours do this? #dogsofinstagram #funnydogs #dogmemes" --at "2026-10-29 18:30"
      ```

## 8. First batch of Reels — after step 7

- [ ] Copy `plans/example.yaml` into `SocialStudio\week1\week1.yaml` in Google Drive (or use Claude's draft) next to
      the clips.
- [ ] `py -m social_studio batch "G:\My Drive\SocialStudio\week1\week1.yaml"` → open the `preview.html` it prints
      and watch every Reel.
- [ ] Happy? Same command with `--go`: they go into the next free daily slots (6 pm), extras to the reserve.
- [ ] `py -m social_studio list --account ur_dailydog` shows the queue; `py -m social_studio kill <id>` stops one.

---

## Everyday commands

| What | Command |
|---|---|
| Get the newest code | `pull.bat` |
| Check everything is connected | `py -m social_studio doctor` |
| See the queue | `py -m social_studio list --account ur_dailydog` |
| Stop one post | `py -m social_studio kill <id>` |
| Make and queue a batch of Reels | `py -m social_studio batch <plan.yaml>` then add `--go` |
| What's working | `py -m social_studio profile --account ur_dailydog` |
| Stop **everything** | GitHub variable `PUBLISHER_ON` = `false` (or ask Claude to set `paused: true`) |

## Two PCs

- Nothing posts from a PC: GitHub runs the publisher and Supabase holds the queue, so either PC can be off.
- Same `.env` on both. Run `pull.bat` before working.
- Keep each batch's plan file and its clips together in Google Drive so either PC can run it.
- Queuing the same batch twice is refused, so `--go` on the second PC can't double-post.
- Only the desktop does AI images/video later (GPU).

## Later (not yet)

- Ollama + ComfyUI on the desktop for the AI phase (Claude writes that list when we get there).
- Higgsfield only if local AI video isn't good enough: monthly billing, cancel the trial if testing.
- Before the first Dog of the Week: read Meta's Promotion Guidelines once.
- Keep posting by hand (or with the free Business Suite scheduler) until the queue is running.
