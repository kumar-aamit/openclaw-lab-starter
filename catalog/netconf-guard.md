# NetConf Guard

**Industry:** network operations · **Layout:** review · **Model:** smart · **Finished app:** `examples/netconf-guard/app/`
**Reasons to run on-site:** `ip`, `regulated`, `offline`, `pinned-model`

## Who uses it
A network engineer checking a switch, router or firewall config before a change window or an audit.

## The problem
Device configs hold the network's topology, addresses and often credentials. They must not be pasted
into a public AI service, so today they are reviewed by hand, slowly and unevenly.

## What the app does
The engineer pastes a running config and picks the platform. The app returns:
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
1. Catalyst 9300 access switch: Telnet on VTY, SNMP community public with write access, clear-text
   enable password (should score 80 or more)
2. ISR 4331 branch router: type 7 enable password, VTY reachable from the WAN, no NTP authentication
3. ASA 5516 edge firewall: permit ip any any on outside, SSH open to the internet, SSH version 1
   (should score 90 or more)

## What each prompt builds
| Prompt | Builds | Check after the push |
| --- | --- | --- |
| 1 Build | app.yaml (NetConf Guard), screen `review` titled Network Config Review: config textarea, platform select, score with `higher: worse`, issues table, text block | Pressing Run shows a colored risk score, an issues table and an explanation |
| 2 Ground it | the three samples as examples with mocks, `knowledge/hardening-standard.md`, a Rule column citing rule numbers | Three sample chips; issues cite numbered rules such as 1.2 or 3.1 |
| 3 Make it yours | brand `#1E3A8A`, mark `shield`, Severity column, `status:` chips renamed for reviews | Dark blue header with a shield, colored severity chips, a Reviews chip that counts up |

## Prompts to send
What the lab user types, one at a time. After each one the harness checks, pushes and reports the
app URL; open it and try a sample before sending the next.

Prompt 1, Build:

```text
Build an app called NetConf Guard with a screen called Network Config Review that reviews switch
and router configs for security problems. I paste a config, it gives me a risk score, a list of
issues with how to fix each one, and an explanation. Use the NetConf Guard brief.
```

Prompt 2, Ground it:

```text
Add three sample configs I can try: a Catalyst switch, an ISR router and an ASA firewall, each
with realistic mistakes. Also check against our hardening standard and show the rule number for
each issue.
```

Prompt 3, Make it yours:

```text
Make it look like our team: dark blue with a shield logo. Add a severity column to the issues,
and show a count of reviews and the last review time at the top.
```

## Feature prompts
Optional, one at a time, after prompt 3:
- Add a screen that writes a change request for the fixes from a review, with a rollback plan.
- Add a screen where I paste show interface output and get a table of interfaces, status, VLAN and errors.
- Add a sample for a Nexus data center switch with routing protocol mistakes.
- Use the fast model for the review and compare the answers.
