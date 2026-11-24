# Sharing BodySync with people who don't code

BodySync has two modes and you don't have to manage accounts or a database in either.

| Mode | Setup | Sign-in | Where workouts live |
|---|---|---|---|
| **On this device** | none | none | a file on that computer |
| **Google Drive** | ~15 minutes, once | "Continue with Google" | a private folder in **each person's own** Google Drive |

You host one copy; everyone signs in with their own Google account. You never see anyone's workouts, there are no passwords to reset and nothing to back up. The folder is private to BodySync (people can delete it from their Google account any time).

## One-time setup for Google sign-in + saving to Drive

1. **Create a Google Cloud project** at <https://console.cloud.google.com> (name it BodySync). No billing is needed.
2. **Enable the Drive API:** APIs & Services -> Library -> "Google Drive API" -> Enable.
3. **Set up the consent screen:** APIs & Services -> OAuth consent screen (or "Google Auth Platform").
   - App name: BodySync. Add your support email.
   - Audience: **External**.
   - Scopes: `openid`, `email`, `profile`, and `.../auth/drive.appdata` (this one only reaches the app's own hidden
     folder, not anyone's Drive files). The Data Access page in Google Cloud shows how Google classifies each scope and
     whether it needs review; check it there rather than trusting this guide.
   - Privacy policy link: use the PRIVACY.md page in **your** fork on GitHub
     (`https://github.com/YOUR-NAME/YOUR-FORK/blob/main/PRIVACY.md`). The app also shows it under "How your data is kept".
   - **Start in "Testing"** and add yourself and your family as test users: only those emails can sign in, which is
     the safest way to try it. When you're ready for anyone, **publish** it ("In production"). Google may ask for app
     verification (app name, home page, privacy link); until then people may see an "unverified app" notice.
4. **Create the sign-in keys:** Credentials -> Create credentials -> OAuth client ID -> **Web application**.
   - Authorized redirect URIs (add both):
     - `http://localhost:8501/oauth2callback`
     - `https://YOUR-APP.streamlit.app/oauth2callback` (after you know your app's address)
   - Copy the **Client ID** and **Client secret**.
5. **Make a cookie secret:** `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
6. **Add the keys as secrets.** Copy `.streamlit/secrets.toml.example` and fill it in.
   - Locally: save it as `.streamlit/secrets.toml` (it is git-ignored).
   - Hosted: Streamlit Community Cloud -> your app -> Settings -> Secrets -> paste it.
   - As soon as the `[auth]` section exists, the app switches to Google mode by itself.
7. **Host it free:** <https://share.streamlit.io> -> Create app -> this repo, branch `main`, main file `homepage.py`. Paste the secrets under Advanced settings. Use Python 3.10+ and Streamlit 1.53 or newer (already in `requirements.txt`).
8. **Test it:** open the app, click Continue with Google, add a lift, finish a workout, then sign out and back in. Your data should still be there.

## Good to know
- **Not yet tested against the real Google service.** The storage code is tested against a simulated Drive and the screens against the app itself; step 8 is the real test. If saving fails, the app keeps your changes in the session and shows "Reconnect Google".
- **Google sign-in lasts about an hour for saving.** After that the person taps "Reconnect Google" once. Nothing is lost in between.
- **Two devices at once:** the last save wins (fine for one person on a phone and a laptop, not for editing the same moment on both).
- **Free hosting sleeps** after about 12 hours without visitors and wakes on the next visit.
- **AI for everyone, no keys to paste (recommended).** Most people won't create an API key, so do what apps with
  free AI do: put one `GEMINI_API_KEY` in the secrets. It's used on the server only and never reaches a browser.
  Each person gets `AI_DAILY_LIMIT` requests a day (default 20) so one person can't use up the key's free quota;
  they see how many are left. Anyone can still paste their own free key (kept in their session only, not counted).
  On Gemini's free tier, Google may use prompts to improve its products; the app tells people not to send anything
  private. Watch your usage in AI Studio.
- **A public copy needs sign-in.** Without the `[auth]` section, the app only opens on your own computer or home network
  (localhost, 192.168.x, 10.x). On a public address it shows a setup page, because everyone would share one account.
  `BODYSYNC_ALLOW_SHARED=1` turns this off for a private server only you use.
- **No Google yet?** Skip all of this. Each person can run BodySync on their own computer (see the README) with no sign-in.
