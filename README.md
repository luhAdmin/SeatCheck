# SeatCheck — Running it on your Mac

This is a walkthrough for running SeatCheck for the first time. Every command
starts with `$` — you don't type the `$`, that's just to show it's a Terminal
command. Copy the text after the `$`.

**Time: ~15 minutes for first-time setup, ~30 seconds every run after that.**

---

## What you'll need

- macOS (any recent version)
- Terminal (built into every Mac — press `Cmd + Space`, type "Terminal", enter)
- The three values from `APP_REGISTRATION_GUIDE.md`
- ~5 minutes of patience for the first install

---

## Step 1 — Check if Python is installed

Open Terminal. Type:

```
$ python3 --version
```

Press Enter. You should see something like `Python 3.11.5` or higher.

**If it says command not found or the version is below 3.10:**
Install Python from **https://www.python.org/downloads/** — download the latest
"macOS 64-bit universal installer", run it, and re-run the check above.

## Step 2 — Put the SeatCheck folder somewhere

Unzip the SeatCheck folder and put it somewhere you'll remember. I recommend
your home folder. For this guide I'll assume it's at:

```
~/seatcheck
```

(The `~` means your home folder.)

## Step 3 — Open Terminal in that folder

In Terminal:

```
$ cd ~/seatcheck
```

Press Enter. Now you're "inside" the SeatCheck folder from Terminal's perspective.

## Step 4 — Create a virtual environment (isolates SeatCheck's dependencies)

```
$ python3 -m venv venv
```

This creates a folder called `venv` inside `seatcheck`. It's harmless — it just
keeps SeatCheck's Python packages separate from the rest of your Mac.

Then activate it:

```
$ source venv/bin/activate
```

You'll notice your Terminal prompt now starts with `(venv)`. That means it's
active. If you close Terminal and come back later, run this command again.

## Step 5 — Install SeatCheck's dependencies

```
$ pip install -r requirements.txt
```

This takes a minute. You'll see a bunch of scrolling text — that's fine.

## Step 6 — Create your `.env` file with your app registration values

```
$ cp .env.example .env
$ open -a TextEdit .env
```

TextEdit opens the file. Paste in your three values from the app registration
guide, save, close.

## Step 7 — Run SeatCheck

```
$ python seatcheck.py
```

You'll see progress messages:

```
🔐 Authenticating to tenant abc12345…
✅ Authenticated

📥 Pulling data from Microsoft Graph…
  → Fetching tenant licenses (subscribedSkus)...
  → Fetching users (this can take a minute on large tenants)...
  → Fetching 90-day active user detail...
  → Fetching 90-day M365 apps usage...
  → Fetching 90-day Teams activity...
✅ Data pulled

🧮 Analyzing…
✅ Analysis complete — 23 findings

📄 Building PDF: output/SeatCheck-Acme-20260712-1430.pdf
📊 Writing CSV: output/SeatCheck-Acme-20260712-1430.csv

──────────────────────────────────────────────────
  Estimated annual savings: $18,432.00
  Monthly: $1,536.00
──────────────────────────────────────────────────

✅ Done. Open output/SeatCheck-...pdf
```

The PDF is in the `output` folder. Open it:

```
$ open output/SeatCheck-*.pdf
```

That's your first report.

---

## Every subsequent run

Open Terminal, then:

```
$ cd ~/seatcheck
$ source venv/bin/activate
$ python seatcheck.py
```

Three commands, ~30 seconds. New PDF every time.

---

## If something goes wrong

**"AADSTS7000215: Invalid client secret"** — Your secret is wrong or expired.
Go back to Entra, create a new client secret, update `.env`.

**"Insufficient privileges to complete the operation"** — You didn't click the
"Grant admin consent" button on the API permissions page, or you're missing a
permission. Go back to Step 5 of `APP_REGISTRATION_GUIDE.md`.

**"HTTPSConnectionPool… Max retries exceeded"** — Network issue. Check your
internet, try again.

**Report shows user names as hex strings like `3E8E8FA1B2C3…`** — Report
concealment is on. See Step 6 of `APP_REGISTRATION_GUIDE.md`.

**Report shows $0 savings** — Either your tenant is genuinely well-optimized
(unlikely, but possible for very small/new tenants), or the usage report data
hasn't populated yet (Microsoft has a ~7-day lag on brand-new tenants). Try
again in a week if the tenant is new.

Anything else — send me the exact error message from Terminal and I'll help you
sort it.
