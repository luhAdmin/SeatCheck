# App Registration Guide — SeatCheck

You need to create an "app registration" in your M365 tenant. This is a one-time
setup. It gives SeatCheck a read-only identity that can pull license and usage
data — nothing else.

**Time: ~10 minutes. Requires Global Administrator.**

At the end you'll have three values to paste into a file called `.env`:
- Tenant ID
- Client ID
- Client Secret

---

## Step 1 — Open the Entra admin center

Go to **https://entra.microsoft.com** and sign in as Global Admin.

## Step 2 — Create the app registration

In the left menu: **Applications → App registrations → + New registration**

Fill in:
- **Name:** `SeatCheck`
- **Supported account types:** *Accounts in this organizational directory only (Single tenant)*
- **Redirect URI:** leave blank

Click **Register**.

## Step 3 — Copy the Tenant ID and Client ID

You're now on the app's overview page. You'll see two important values at the top:

- **Application (client) ID** → this is your `CLIENT_ID`
- **Directory (tenant) ID** → this is your `TENANT_ID`

Copy both somewhere safe (a text editor). You'll paste them into `.env` at the end.

## Step 4 — Create a Client Secret

In the left menu of the app page: **Certificates & secrets → + New client secret**

- **Description:** `SeatCheck secret`
- **Expires:** 24 months (or whatever you prefer — you'll need to renew before it expires)

Click **Add**.

**⚠ IMPORTANT:** The secret **Value** shows only once. Copy it *right now*. If
you navigate away, you'll never see it again and will have to create a new one.

This is your `CLIENT_SECRET`.

## Step 5 — Grant API Permissions

In the left menu: **API permissions → + Add a permission → Microsoft Graph → Application permissions**

Add these five permissions (search for each one, check the box, click **Add
permissions**, then repeat):

| Permission | Why |
| --- | --- |
| `Directory.Read.All` | Read tenant SKU / license inventory |
| `User.Read.All` | Read user list + assigned licenses |
| `AuditLog.Read.All` | Read sign-in activity dates |
| `Reports.Read.All` | Read usage reports (the core data source) |
| `Organization.Read.All` | Read tenant info (name, verified domains) |

After adding, click the **Grant admin consent for [Your Tenant]** button at the
top of the permissions list, and confirm. Every permission should show a green
check under "Status".

## Step 6 — Turn off report anonymization (optional but recommended)

By default, M365 hides user names in the reports API. To see real names in your
SeatCheck report, do this:

1. Go to **https://admin.microsoft.com**
2. **Settings → Org settings → Services → Reports**
3. **Uncheck** "Display concealed user, group, and site names in all reports"
4. Save

(You can leave this on if privacy is a concern — SeatCheck will detect it and
still generate the report using the hashed identifiers, with a note at the top.)

## Step 7 — Paste values into `.env`

In the SeatCheck folder, copy `.env.example` to a new file called `.env` and
fill in the three values you copied:

```
TENANT_ID=<paste the Directory (tenant) ID>
CLIENT_ID=<paste the Application (client) ID>
CLIENT_SECRET=<paste the client secret Value>
TENANT_NAME=Your Company Name
```

Save. You're done.

---

## What did we just do?

You created a service identity ("app registration") that lives in your tenant.
It has read-only permissions to see licenses and usage. It can't send email,
can't read email content, can't modify anything, can't sign in as any user. If
you ever want to revoke SeatCheck's access, delete this app registration and
it's gone instantly.
