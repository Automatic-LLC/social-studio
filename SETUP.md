# Social Studio setup: Aaron's list

Everything here works from the ThinkPad; no GPU needed until the AI-video phase. Do the sections in order.
**Never paste a token or key into a chat with Claude.** Put them in a password manager, the `.env` file and GitHub
secrets only. The IDs that `doctor` prints (Page id, Instagram id) are not secret: those you can paste.

Time: about 1 to 1.5 hours in total, mostly the Meta part.

---

## A. GitHub (5 min)

1. **Rename the repo.** github.com/Automatic-LLC/IG-accts → Settings → General → Repository name: `social-studio`
   → Rename. (Old links and `git pull` keep working; GitHub redirects.)
2. **Make it public.** Same page, bottom, Danger Zone → Change visibility → Public. It's safe: no keys are in the
   repo, and the `.gitignore` keeps `.env` files out. (Public also gives free, unlimited GitHub Actions minutes,
   which is what runs the publisher.)
3. **Turn on the website.** Settings → Pages → Source: "Deploy from a branch" → Branch `main`, folder `/docs` → Save.
   After a minute or two, check that these load:
   - https://automatic-llc.github.io/social-studio/privacy.html
   - https://automatic-llc.github.io/social-studio/data-deletion.html
   Meta needs both links in section D.

## B. Supabase: a NEW project for Social Studio (10 min)

The Supabase project already connected to Claude belongs to your other business. Don't use it for this.

1. supabase.com → New project. Name `social-studio`, region: a US one near you, Free plan. Save the database
   password in your password manager (we won't need it day to day).
2. Left menu → **SQL Editor** → New query → paste all of `supabase/migrations/001_init.sql` from the repo → Run.
   It should say "Success". This makes the `posts` and `post_log` tables and the `media` storage bucket.
3. Left menu → **Storage**: check that a bucket called `media` exists and is marked **Public**.
4. Left menu → **Project Settings → API Keys**: copy the **Project URL** and the **secret key** (`sb_secret_...`)
   into your password manager. They become `SUPABASE_URL` and `SUPABASE_KEY`.

Note: free projects pause after about a week with no activity. Once the publisher runs every 15 minutes, that
doesn't happen. If it pauses before then, open the dashboard and click Restore.

## C. Phone alerts (2 min)

1. Install the **ntfy** app (iPhone or Android).
2. Tap + → subscribe to a topic with a long random name nobody would guess, e.g. `ur-dailydog-7f3k9q2x`
   (anyone who knows the name can read the alerts). That name is `NTFY_TOPIC`.

## D. Meta (30-45 min)

1. **Check the link.** business.facebook.com → Settings → Accounts → Instagram accounts: @ur_dailydog should be there
   and connected to the dog Facebook Page. (Account type Business: already confirmed.)
2. **Developer account.** developers.facebook.com → Get started, log in with the Facebook account that runs the
   Page, verify your phone.
3. **Create the app.** My Apps → Create app → use case **Other** → type **Business** → name `Social Studio` →
   connect it to the business portfolio that owns the Page.
4. **App settings → Basic:**
   - Privacy Policy URL: `https://automatic-llc.github.io/social-studio/privacy.html`
   - User data deletion: "Data deletion instructions URL" → `https://automatic-llc.github.io/social-studio/data-deletion.html`
   - Category: anything close (e.g. "Entertainment"). Save changes.
5. **Add products** (left menu → Add product): **Instagram** → choose "API setup with Facebook login", and
   **Facebook Login for Business**.
6. **System user (the never-expiring token).** business.facebook.com → Settings → Users → **System users** → Add →
   name `social-studio-bot`, role **Admin**. Then on that system user → **Assign assets**:
   - Apps → Social Studio → full control
   - Pages → the dog Page → full control (or at least content and insights)
   - Instagram accounts → @ur_dailydog → full control
7. **Generate the token.** On the system user → Generate new token → app **Social Studio** → expiration **Never** →
   tick these permissions:
   `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights`, `instagram_manage_comments`,
   `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `business_management`
   → Generate → **copy it into your password manager right away** (Meta shows it once). This is `META_TOKEN`.
8. **Go Live.** Back in the app dashboard, switch App Mode from Development to **Live** (needs the privacy URL from
   step 4). Posting to your own accounts needs only Standard Access: no App Review.

## E. ThinkPad: first check and first test post (15 min)

1. Install Python from python.org (tick "Add to PATH") if `py --version` doesn't work, and Git if needed.
2. Get the code:
   ```
   cd C:\
   git clone https://github.com/Automatic-LLC/social-studio.git SocialStudio
   cd C:\SocialStudio
   py -m pip install -r requirements.txt
   ```
3. Make the secrets file: copy `.env.example` to `.env` in `C:\SocialStudio` (or save it as
   `C:\Trading\SocialStudio.env`, next to your trading keys) and fill in `META_TOKEN`, `SUPABASE_URL`,
   `SUPABASE_KEY`, `NTFY_TOPIC`. Notepad is fine. Never commit it (git ignores it).
4. Run the check:
   ```
   py -m social_studio doctor
   ```
   It prints your Page id (`fb_page_id`) and Instagram id (`ig_user_id`). Put both in
   `accounts/ur_dailydog.yaml`, or paste the two numbers to Claude and Claude will commit them.
5. Run `doctor` again: it should end with "all good" and show your posting quota (e.g. "used 0 of 50").
6. **First real post (Phase 1 done):** pick any dog photo you're happy to have on the page (it stays up unless you
   delete it in the app):
   ```
   py -m social_studio test-post --account ur_dailydog --file C:\path\to\dog.jpg --caption "Monday mood 🐶" --yes
   ```
   It prints the post's link.

## F. Turn on the automatic publisher (5 min)

1. github.com/Automatic-LLC/social-studio → Settings → Secrets and variables → Actions:
   - **Secrets** tab → New repository secret, four times: `META_TOKEN`, `SUPABASE_URL`, `SUPABASE_KEY`, `NTFY_TOPIC`
   - **Variables** tab → New repository variable: `PUBLISHER_ON` = `true`
2. Actions tab → **publish** → Run workflow. It should finish green and say "{'posted': 0, ...}".
3. **Phase 2 test:** queue a post for 30 minutes from now (account time, Central), close the laptop, and check the
   page later:
   ```
   py -m social_studio add --account ur_dailydog --kind image --file dog2.jpg --caption "Caption that passes the rules 😂 Does yours do this? #dogsofinstagram #funnydogs #dogmemes" --at "2026-11-01 18:30"
   py -m social_studio list --account ur_dailydog
   ```
   `add` refuses captions that break the rules and says why. `kill <id>` stops a post.

To stop everything at once: set `paused: true` in `config.yaml` (Claude can do it), or set `PUBLISHER_ON` to
`false` in GitHub.

## G. Making Reels (ThinkPad is fine)

1. **Install ffmpeg** (the video tool): open PowerShell and run `winget install Gyan.FFmpeg`, then close and reopen
   PowerShell. `ffmpeg -version` should print a version.
2. **Pexels key** (free stock clips): sign up at pexels.com/api → copy your API key into the `.env` file as
   `PEXELS_KEY=...` (and later as a GitHub secret with the same name).
3. **Make a batch:** copy `plans/example.yaml` to `plans/week1.yaml`, put your clips in `plans/clips/`, write the
   on-screen text and captions (or ask Claude to draft them), then:
   ```
   py -m social_studio batch plans/week1.yaml
   ```
   It renders every Reel (9:16, your text on top, "Follow @ur_dailydog" end card) and uploads nothing yet. Open the
   `preview.html` it prints, watch them, fix the plan if needed, then queue them into the next free daily slots:
   ```
   py -m social_studio batch plans/week1.yaml --go
   ```
   Extra Reels (or ones marked `reserve: true`) go to the reserve that fills killed or failed slots.

## H. Later (not needed yet)

- **Desktop (GPU)**: Ollama + ComfyUI install, for the AI phase (Claude will write the step list then).
- **Higgsfield**: only if local AI video isn't good enough; pick monthly billing, cancel the trial if testing.
- **Before the first contest**: read Meta's Promotion Guidelines page once.
- **Keep posting by hand** (or with the free Business Suite scheduler) until the queue is running, so the account
  doesn't go quiet.
