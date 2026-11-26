# Alert Triage

**Industry:** IT and network operations · **Layout:** review · **Model:** smart · **Tier:** 3 (hooks and an answer schema)
**Reasons to run on-site:** `volume`, `ip`, `regulated`, `latency`, `offline`, `pinned-model`

## Who uses it
A security analyst on the HQ security team, working the alert queue during a shift.

## The problem
The team gets hundreds of alerts a day and cannot read every one with its logs. Pasting alerts and
logs into a public AI service is not allowed: they map the network, its users and its weak spots.

## What the app does
The analyst pastes an alert, attaches its logs and picks the affected system. The app returns:
- a severity score from 0 to 100 with a one-line label
- a verdict: what most likely happened and why, quoting the log lines that matter
- a table of MITRE ATT&CK techniques the evidence supports
- a checklist of next steps, each citing the runbook step it came from

## Data to make up
- `data/assets.csv`: about six systems with hostname, role, owner, criticality and location
- a VPN log with a password spray from one outside address and one success afterwards
- a VPN log with a single locked-out user who was reset by the help desk (the benign case)
- `knowledge/`: three short runbooks with sections Signs, Contain, Investigate and Escalate or Recover:
  password spray, reported phishing email, suspected malware beacon

Use documentation address ranges (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24) and `.example`
domains. Invent every name.

## Examples to include
1. Password spray, then a login (should score 80 or more)
2. Reported phishing email, no logs (should score in the middle)
3. Locked-out user, already reset (should score under 40)

## Prompts to send
What the lab user types, one at a time. After each one the harness checks, pushes and reports
the app URL; open it and click an example before sending the next. `GUIDE.md` has the same prompts.

Prompt 1, Build:

```text
Build an alert triage app for our HQ security team. An analyst pastes an alert, can attach its
logs and pick the affected system, and gets a verdict on what happened. Make up sample alerts
and logs to try it with. Use the Alert Triage brief.
```

Prompt 2, Ground it:

```text
Add our incident runbooks for password spray, phishing and malware, and give the analyst next
steps from them, each showing the runbook section it came from.
```

Prompt 3, Shape the answer:

```text
Add a severity score from 0 to 100 and a table of the MITRE ATT&CK techniques. Count the failed
logins in the logs exactly instead of letting the AI guess. Add a harmless example too: a user
who got locked out and was already reset.
```

## What each prompt builds
For the harness. A prompt says what the user wants; take every detail it leaves out from the
matching step below, and build only that step. Each step ends with `make check` passing, a push,
`make wait` and `make smoke`.

### Step 1: Build
- `app.yaml`: name Alert Triage, mark `shield`, brand `"#1D4ED8"`, site `HQ data center`,
  screens `[triage]`.
- `screens/triage.yaml`: title "Triage an alert", review layout, smart model. Inputs:
  `alert` (textarea, "Paste the alert"), `logs` (optional file, "Attach the logs", .log .txt .csv),
  `asset` (optional select, "Affected system", options from `data/assets.csv`).
  Answer: one `text` block, key `verdict`, title Verdict.
- `prompts/triage.md`: two or three sentences on what most likely happened, how sure, and why,
  quoting the log lines that matter with their timestamps; say so if the logs do not support the alert.
- `data/assets.csv`: columns hostname, role, owner, criticality, location; vpn-gw-01 (remote access
  VPN gateway, high), mail-01 (mail relay, high), dc-01 (domain controller, critical), fin-db-02
  (finance database, critical), web-ext-01 (public website, medium), hr-laptop-114 (laptop, medium).
- `data/vpn-spray.log`: about 230 lines like
  `2026-11-24T01:52:08Z vpn-gw-01 auth user=a.chen src=203.0.113.45 result=FAIL reason=bad_password`.
  Normal logins from 198.51.100.x; 212 failures for 9 users from 203.0.113.45 between 01:52 and
  02:12; a success for j.ortiz from that address at 02:14:07 with `mfa=none reason=legacy_client`;
  a session from it to fin-db-02 at 02:16:31.
- Two examples with mock answers: "Password spray, then a login" (alert "212 failed VPN logins for
  9 users from 203.0.113.45, then a success for j.ortiz at 02:14", the spray log, vpn-gw-01) and
  "Reported phishing email" (alert "m.reyes reported an email from payroll-update@examp1e-hr.example
  asking staff to confirm bank details through a link", no logs, mail-01).

### Step 2: Ground it
- `knowledge/password-spray.md` "Runbook: password spray against VPN or single sign-on" with
  Signs, Contain, Investigate, Escalate; `knowledge/phishing.md` "Runbook: reported phishing email"
  and `knowledge/malware-beacon.md` "Runbook: suspected malware beacon", each with Signs, Contain,
  Investigate, Recover.
- The screen gets `knowledge: knowledge/` and a `checklist` block, key `steps`, title Next steps.
- The prompt asks for at most six steps in order, each naming the address, account or system,
  taken from a runbook passage when one applies and citing it as `[n]`; empty source otherwise.
- Both mocks gain steps whose `[n]` cite passages the search really finds.

### Step 3: Shape the answer
- Blocks in this order: `score` (key `severity`, title Severity), the verdict, `table` (key
  `techniques`, title Attack techniques, columns Technique, ID, Evidence), the next steps.
- The prompt adds the severity bands: 80 or more act now, 40 to 79 investigate today, under 40
  likely benign or handled; higher when the asset's criticality is high or critical.
- `hooks.py` `prepare(ctx)` returns `login_summary` (from the log: failed logins, their time range,
  accounts tried, failures by source, any success from a failing address after the failures) and
  `asset_info` (role, owner, criticality from `data/assets.csv`). The prompt says the counts are exact.
- Third example, "Locked-out user, already reset": alert "Account lockout for s.ito on the VPN
  after 6 failed logins", vpn-gw-01, and `data/vpn-lockout.log`: 5 bad passwords for s.ito from
  198.51.100.23, locked at 09:00:16, a help-desk reset at 09:21 after a callback, an MFA login at
  09:24. It scores under 40.
- All three mocks reshaped to the four blocks.
