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
- [ ] Don't add `PUBLISHER_ON` yet (step 7).

## 3. Each PC: install with one double-click (10 min per PC) — now, on both PCs

No terminal needed. On each PC:

- [ ] Open this link in the browser: **https://automatic-llc.github.io/social-studio/install.bat**. It downloads
      `install.bat` (if the browser asks, choose **Keep**).
- [ ] Double-click `install.bat` in your Downloads folder. If Windows says "Windows protected your PC", click
      **More info → Run anyway** (it's our own file from our own website).
- [ ] If it installs Python, Git or ffmpeg, it says so and asks you to **close the window and double-click
      `install.bat` again**. Do that (once).
- [ ] Notepad opens your secrets file (`.env`). Fill in `SUPABASE_URL`, `SUPABASE_KEY`, `NTFY_TOPIC` (and
      `PEXELS_KEY` if you have it). Leave the others empty for now. **Save (Ctrl+S) and close Notepad.**
- [ ] It runs the check and shows **OK Supabase: posts table reachable**. The Meta lines stay empty until step 6.
      Then it opens the `C:\SocialStudio` folder.
- [ ] From now on, double-click `pull.bat` in `C:\SocialStudio` before working on that PC.

Later, to add a value to `.env` (like `META_TOKEN` tonight): open `C:\SocialStudio`, right-click `.env` →
**Open with → Notepad**, add the line, save. If something fails, screenshot the window and send it to Claude.

**Commands** (steps 7 and 8): in `C:\SocialStudio`, click the folder's address bar, type `cmd`, press Enter. A black
window opens already in the right folder; paste the command there.

## 4. Stock clips from Pexels (optional, no key needed)

Pexels paused new API keys (Oct 2026), so skip `PEXELS_KEY`. To use a stock clip:

- [ ] On pexels.com/videos find a dog clip → **Free download** → save it in the week's folder (e.g.
      `G:\My Drive\SocialStudio\week1\`). Note the creator's name shown on the clip's page.
- [ ] In the plan, give it `source: pexels` and `credit: "<creator's name>"` (see `plans/example.yaml`). The batch puts
      "Video: <name> / Pexels" on screen and "Video by <name> on Pexels" in the caption.

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

Open **cmd**: press the Windows key, type `cmd`, press Enter. Paste each command, press Enter after each line.

- [ ] Check the setup and get your two IDs:
      ```
      cd /d C:\SocialStudio
      py -m social_studio doctor
      ```
      It prints **fb_page_id** and **ig_user_id**: paste the two numbers to Claude (Claude commits them). Then:
      ```
      cd /d C:\SocialStudio
      git pull origin main
      py -m social_studio doctor
      ```
      It should end with **all good** and show your quota ("used 0 of 50").
- [ ] **Test post** (stays on the page unless you delete it in the app). Put a dog photo at `C:\SocialStudio\test.jpg`
      first, then:
      ```
      cd /d C:\SocialStudio
      py -m social_studio test-post --account ur_dailydog --file C:\SocialStudio\test.jpg --caption "Monday mood 🐶" --yes
      ```
- [ ] GitHub → Settings → Secrets and variables → Actions → **Variables** tab → `PUBLISHER_ON` = `true`
- [ ] GitHub → **Actions** tab → **publish** → Run workflow → it goes green.
- [ ] What has worked so far (paste the report to Claude; no secrets in it):
      ```
      cd /d C:\SocialStudio
      py -m social_studio profile --account ur_dailydog
      ```
- [ ] **Hands-off test:** put a second photo at `C:\SocialStudio\test2.jpg`, change the date and time to about 30
      minutes from now (Central time), close the laptop, check the page later:
      ```
      cd /d C:\SocialStudio
      py -m social_studio add --account ur_dailydog --kind image --file C:\SocialStudio\test2.jpg --caption "Caption that passes the rules 😂 Does yours do this? #dogsofinstagram #funnydogs #dogmemes" --at "2026-10-29 21:30"
      py -m social_studio list --account ur_dailydog
      ```

## 8. First batch of Reels — after step 7

- [ ] Make the folder `G:\My Drive\SocialStudio\week1\` in Google Drive, put the clips in it, and copy the example
      plan there (or use Claude's draft):
      ```
      copy C:\SocialStudio\plans\example.yaml "G:\My Drive\SocialStudio\week1\week1.yaml"
      notepad "G:\My Drive\SocialStudio\week1\week1.yaml"
      ```
- [ ] Render and preview (nothing uploads yet); open the `preview.html` it prints and watch every Reel:
      ```
      cd /d C:\SocialStudio
      py -m social_studio batch "G:\My Drive\SocialStudio\week1\week1.yaml"
      ```
- [ ] Happy? Queue them into the next free daily slots (6 pm), extras to the reserve:
      ```
      cd /d C:\SocialStudio
      py -m social_studio batch "G:\My Drive\SocialStudio\week1\week1.yaml" --go
      py -m social_studio list --account ur_dailydog
      ```

---

## Everyday commands (cmd)

Always start with `cd /d C:\SocialStudio`, then:

| What | Command |
|---|---|
| Get the newest code | `git pull origin main` (or double-click `pull.bat`) |
| Check everything is connected | `py -m social_studio doctor` |
| See the queue | `py -m social_studio list --account ur_dailydog` |
| Stop one post (number from `list`) | `py -m social_studio kill 42` |
| Make a batch of Reels (preview) | `py -m social_studio batch "G:\My Drive\SocialStudio\week1\week1.yaml"` |
| Queue that batch | the same command with ` --go` at the end |
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
