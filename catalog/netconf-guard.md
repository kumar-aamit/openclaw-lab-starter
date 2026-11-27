# NetConf Guard

**Industry:** network operations · **Layout:** review · **Model:** smart · **Finished app:** `examples/netconf-guard/app/`
**Reasons to run on-site:** `ip`, `regulated`, `offline`, `pinned-model`

## Who uses it
A network engineer checking a switch, router or firewall config before a change window or an audit.

## The problem
Device configs hold the network's topology, addresses and often credentials. They must not be pasted
into a public AI service, so today they are reviewed by hand, slowly and unevenly.

## What the app does
The finished app, after prompt 3. The engineer pastes a running config and picks the platform. The
app returns:
- a risk score from 0 to 100 (higher is worse) with a two-to-four word label
- a table of issues: the offending line, what is wrong, a severity of High, Medium or Low, the rule
  number from the hardening standard, and the exact commands that fix it
- three or four sentences on what an attacker could do today and what to fix first

## Data to make up
- `knowledge/hardening-standard.md`: about 25 numbered rules in five sections (management access,
  AAA and passwords, SNMP logging and time, switching, firewall policy)
- three sample configs, each with planted mistakes of mixed severity

Use documentation address ranges (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24) or private ranges.
Invent every hostname and password.

## Examples to include
1. Catalyst 9300 access switch (step 1): Telnet on VTY, SNMP community public with write access,
   clear-text enable password (should score 80 or more)
2. ISR 4331 branch router (step 1): type 7 enable password, VTY reachable from the WAN, no NTP
   authentication
3. ASA 5516 edge firewall (step 2): permit ip any any on outside, SSH open to the internet, SSH
   version 1 (should score 90 or more)

## Prompts to send
What the lab user types, one at a time. After each one the harness checks, pushes and reports the
app URL; open it and try a sample before sending the next.

Prompt 1, Build:

```text
Build an app called NetConf Guard with a screen called Network Config Review that reviews switch
and router configs for security problems. I paste a config and pick the platform, and it gives me
a risk score, a list of issues with how to fix each one, and an explanation. Add a Catalyst switch
and an ISR router config to try it with. Use the NetConf Guard brief.
```

Prompt 2, Ground it:

```text
Check every config against our hardening standard and show the rule number for each issue. Add an
ASA firewall sample too.
```

Prompt 3, Make it yours:

```text
Make it look like our team: dark blue with a shield logo. Add a severity column to the issues,
and show a count of reviews and the last review time at the top.
```

## What each prompt builds
For the harness. A prompt says what the user wants; take every detail it leaves out from the
matching step below, and build only that step. `examples/netconf-guard/app/` is the app after step
3, so copy from it only what the current step lists. Each step ends with `make check` passing, a
push, `make wait` and `make smoke`.

### Step 1: Build
- `app.yaml`: name NetConf Guard, screens `[review]`. No mark or brand yet.
- `screens/review.yaml`: title Network Config Review, review layout, smart model, `reasoning: off`,
  `output: json`. Inputs: `config` (textarea, "Device config"), `platform` (select, "Platform",
  options Cisco IOS XE switch, Cisco IOS XE router, Cisco ASA firewall). Answer: `score` (key `risk`,
  title "Risk (higher is worse)", `higher: worse`), `table` (key `issues`, title Issues to fix,
  columns Line, Issue, Fix), `text` (key `why`, title Why this matters).
- `prompts/review.md`: a senior network security engineer reviews the config for the platform:
  every risky line and every missing safeguard, each with the offending line (or "(missing)"), what
  is wrong in plain words and the exact commands that fix it; a risk score from 0 to 100 with a two
  to four word label; three or four sentences on what an attacker could do today and what to fix first.
- Two examples with mock answers: the Catalyst 9300 switch and the ISR 4331 router from the list
  above, with the configs and planted mistakes from `examples/netconf-guard/app/`.
- Not in this step: `knowledge/`, the Rule and Severity columns, the ASA sample, `status:`.

Check after the push: two sample chips; pressing Run shows a colored risk score, an issues table
with fixes, and an explanation.

### Step 2: Ground it
- `knowledge/hardening-standard.md`: about 25 numbered rules in five sections (management access,
  AAA and passwords, SNMP logging and time, switching, firewall policy), each rule with its number
  in bold, such as **1.2 No Telnet.**
- The screen gets `knowledge: knowledge/`, and the table gains a Rule column: Line, Issue, Rule, Fix.
- The prompt reviews the config against the hardening standard in the source passages and gives
  the rule number for each issue.
- Third example, the ASA 5516 edge firewall, with its mock.
- Every mock gains a Rule value that matches a real rule in the standard.

Check after the push: three sample chips; issues cite numbered rules such as 1.2 or 3.1, with the
standard's passages listed under the answer.

### Step 3: Make it yours
- `app.yaml`: mark `shield`, brand `"#1E3A8A"`.
- The table gains a Severity column: Line, Issue, Severity, Rule, Fix. The prompt asks for a
  severity of High, Medium or Low, and every mock gets one.
- `status:` chips: `airgap`, `stored: Configs stored`, `runs: Reviews`, `last: Last review`,
  `model`, `knowledge: Standard`.

Check after the push: dark blue header with a shield, colored severity chips, a Reviews chip that
counts up.

## Feature prompts
Optional, one at a time, after prompt 3:
- Add a screen that writes a change request for the fixes from a review, with a rollback plan.
- Add a screen where I paste show interface output and get a table of interfaces, status, VLAN and errors.
- Add a sample for a Nexus data center switch with routing protocol mistakes.
- Use the fast model for the review and compare the answers.
