# Google Setup — for 05_gmail_calendar_agent.py

This lab lets the agent read your Gmail inbox and read/create Google
Calendar events. It needs its own OAuth2 credentials from Google
Cloud Console — this is separate from Ollama/HuggingFace setup and
only required for this one lab.

`credentials.json` and `token.json` are personal secrets. They're
already listed in `.gitignore` — never commit or share them.

## 1. Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
   and sign in with the Google account whose Gmail/Calendar you want
   the agent to access.
2. Create a new project (or select an existing one).

## 2. Enable the two APIs

In the project, go to **APIs & Services → Library** and enable both:
- **Gmail API**
- **Google Calendar API**

## 3. Configure the Google Auth Platform (formerly "OAuth consent screen")

Google renamed and reorganized this section in 2024–2025, so the menu
item is no longer called "OAuth consent screen" — older guides
(including this one, previously) point at menus that don't exist
anymore. The current path:

1. In the left sidebar, go to **APIs & Services → Google Auth
   Platform**. If this is the first time in this project, click **Get
   started** and step through the short wizard:
   - **App information**: app name + your support email → **Next**
   - **Audience**: choose **External** (unless you have a Google
     Workspace org) → **Next**
   - **Contact information**: your email → **Next**
   - Agree to the **Google API Services: User Data Policy** →
     **Continue** → **Create**
2. Once created, you land on the Google Auth Platform pages, split
   into tabs: **Branding**, **Audience**, **Clients**, **Data
   Access**.
3. Add scopes: go to the **Data Access** tab → **Add or Remove
   Scopes**, and add:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/calendar`
   Click **Save**.
4. Add yourself as a test user: go to the **Audience** tab → under
   **Test users**, click **Add users**, enter your own Google
   account's email → **Save**. While the app is unpublished, only
   test users can authorize it.

## 4. Create OAuth client credentials

1. Go to **APIs & Services → Google Auth Platform → Clients** → click
   **Create Client**.
2. Application type: **Desktop app**. Give it any name (only shown to
   you in the console).
3. Click **Create** — the new client appears under "OAuth 2.0 Client
   IDs".
4. Download its JSON (there's a download icon next to the client in
   the list).
5. Rename the downloaded file to `credentials.json` and place it
   directly in `session2/labs/` (next to
   `05_gmail_calendar_agent.py`).

## 5. Run the lab

```bash
source venv/bin/activate
pip install -r requirements.txt   # installs the Google API packages too
python 05_gmail_calendar_agent.py
```

The first run opens a browser window asking you to log in and
approve the requested scopes. After approving, a `token.json` file is
created next to `credentials.json` — subsequent runs reuse it without
prompting again (it auto-refreshes until you revoke access).

## Troubleshooting

**"Access blocked: this app's request is invalid" / "hasn't completed
the Google verification process"**
Make sure your Google account is added as a **test user** under the
Google Auth Platform's **Audience** tab (step 3.4). Unverified apps in
testing mode only work for accounts explicitly listed there.

**`credentials.json not found`**
It must be named exactly `credentials.json` and live in
`session2/labs/` — check the path the error message prints.

**Revoking access**
Go to [myaccount.google.com/permissions](https://myaccount.google.com/permissions),
remove the app, and delete the local `token.json` to force a fresh
consent flow next time.

**Scope changed / "invalid_grant" errors**
If you edit `SCOPES` in the script, delete `token.json` so the app
re-runs the consent flow with the new scopes.
