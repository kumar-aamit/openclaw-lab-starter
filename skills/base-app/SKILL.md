---
name: base-app
description: Build or change the user's app in app/. Use for every request about the app — build it, add a screen, input, answer block, knowledge, sample data or a hook — and before every push.
---

# base-app

The platform in `platform/` turns the files in `app/` into a web app. You write only `app/`: YAML,
Markdown, CSV and text files, plus an optional `hooks.py`. Read `AGENTS.md` first.

## Clone the team repo

Only when the team's repo is not on this machine yet. The repo is `team-<N>`, where N is the
user's team number. Work in exactly that one repo.

1. If the user has not said their team number, ask "What is your team number?". `7`, `team-7` and
   `team 7` all mean 7. Anything that is not a whole number: ask again. Never guess it.
2. Clone it into the folder your harness works in (for OpenClaw, `~/.openclaw/workspace/team-app`):
   ```bash
   git -c http.extraHeader="Authorization: token ${GITEA_TOKEN}" -c http.sslVerify=false \
     clone "${GITEA_INSTANCE_URL}/admin/team-<N>.git" ~/.openclaw/workspace/team-app
   ```
   `GITEA_INSTANCE_URL` and `GITEA_TOKEN` are set on the lab machine; if either is missing, ask the
   user. Never print or save the token.
3. If the clone fails, stop. Tell the user that `team-<N>` was not found or not allowed, and ask
   them to check the number. Clone again only with a number they give you.
4. Never try a nearby number, list or search the server's repos, or clone a repo the user did not
   name. Another team's repo is never a fallback.
5. If the folder already exists, check `git -C <folder> remote get-url origin`. If it ends in
   `/team-<N>.git`, `git pull` and use it. If it names another team, use and delete nothing: tell
   the user which team it belongs to and ask what to do.
6. Copy `lab.env.example` to `lab.env` (git-ignored) and set `APP_URL` to the team's app address
   and `INSECURE_TLS=1`. Ask the user for the address if you do not have it. `make wait` and
   `make smoke` read both.

## The loop

1. Read the request, the brief in `catalog/` if one is named, and the finished app in `examples/`
   closest to it (`alert-triage` or `netconf-guard`).
   Users type short prompts in their own words. If the brief has **What each prompt builds**, match
   the prompt to its step (usually the next one `app/` does not have yet), take every detail the
   prompt leaves out from that step, and build only that step. Later prompts in the same chat
   continue the same brief even when they do not name it.
2. Write or change files in `app/`. One request changes one building block.
3. Run `make check`. It names the file, the field and the fix; do what it says and run it again.
4. Run `make dev` and try an example: `curl -s localhost:8742/api/screens/<screen>/run -H 'content-type: application/json' -d '{"example": 0}'`.
5. `git add app && git commit -m "<what changed>" && git push`, then `make wait` and `make smoke`.
6. Report the app URL from `lab.env` and the timings `make smoke` printed.

## app/ layout

```text
app/
├── app.yaml            name, mark, brand, site, screens
├── screens/<name>.yaml one file per screen listed in app.yaml
├── prompts/<name>.md   the prompt for that screen (Jinja2)
├── data/               synthetic data: CSV for select options and ctx.data, logs for examples
├── knowledge/          .md and .txt documents searched before each answer
└── hooks.py            optional: prepare(ctx) adds values to the prompt
```

## app.yaml

```yaml
name: Alert Triage     # 1 to 40 characters, shown in the header
mark: shield           # one letter, or an icon: shield, server, wifi-off, circle-check, triangle-alert
brand: "#1D4ED8"       # hex; must be dark enough for white text (4.5:1)
site: HQ data center   # where data stays; shown in the privacy note and footer
screens: [triage]      # each name needs screens/<name>.yaml and prompts/<name>.md
```

## Quoting in YAML

Quote any string value that contains `,` `?` `:` or `#`. Unquoted, `#` starts a comment, `: `
starts a new field, and inside `{...}` a `,` ends the value, so the file breaks or silently loses text.

```yaml
label: "Severity: high"
brand: "#0B6E99"
inputs: {alert: "212 failed logins, then a success at 02:14. Spray?"}
```

## screens/<name>.yaml

```yaml
title: Triage an alert
description: One sentence under the title.
layout: review          # review: inputs on the left, the answer on the right
model: smart            # smart for reasoning over long inputs; fast for quick short answers
reasoning: on           # off sends enable_thinking false: faster, shallower
inputs:
  - {name: alert, type: textarea, label: Paste the alert, placeholder: "..."}
  - {name: logs, type: file, accept: ".log,.txt,.csv", optional: true}
  - {name: asset, type: select, options: data/assets.csv, optional: true}
knowledge: knowledge/   # omit if the screen has no documents
output: json
answer:                 # the blocks the model's JSON fills, in display order
  - score: {key: severity, title: Severity}
  - text: {key: verdict, title: Verdict}
  - table: {key: techniques, title: Attack techniques, columns: [Technique, ID, Evidence]}
  - checklist: {key: steps, title: Next steps}
examples:
  - label: Password spray, then a login
    inputs: {alert: "...", logs: data/vpn-spray.log, asset: vpn-gw-01}
    mock: {severity: {value: 88, label: "..."}, verdict: "...", techniques: [...], steps: [...]}
```

Input types: `text`, `textarea`, `select` (options: a list, or a CSV in data/ whose first column is
used), `number`, `toggle` (a true/false value in the prompt), `file` (.txt, .log, .csv, .md, .json and
.pdf become text, up to 2 MB). Names are lowercase with `_`.

Answer blocks and the JSON each one must produce; `key` defaults to the block name:

| Block | JSON value |
|---|---|
| `text` | `"a string; blank lines split paragraphs"` |
| `score` | `{"value": 0-100, "label": "one line"}` |
| `table` | `[{"<column>": "...", ...}]`, one key per column; `columns:` is required |
| `checklist` | `[{"step": "...", "source": "[n]" or ""}]`; the source becomes a citation chip |

Two display rules need no extra YAML beyond what is shown:
- `score: {key: risk, title: Risk, higher: worse}` colors the value red at 70 and up, amber at 40
  to 69, green below. Use `higher: better` for scores where high is good, such as compliance.
- In a table, a column named Severity, Risk or Priority shows High, Medium, Low and Critical as
  colored chips. Columns named Line, Fix, Command or Config line are set in monospace.

## Status chips

A row of chips above each screen shows the local-AI facts that matter for it. Each chip has a
meaning the user sees on hover. Without `status:` a screen shows airgap, stored, runs, last and
model, plus knowledge when it has `knowledge:`. Pick and rename them in the screen file:

```yaml
status:
  - airgap                  # Air-gapped: On
  - stored: Configs stored  # nothing is written to disk or logs
  - runs: Reviews           # answers since this build started, at $0
  - last: Last review       # time of the last answer
  - model                   # model and precision, such as nemotron-3.5-super · NVFP4
  - knowledge: Standard     # documents and sections searched; needs knowledge:
```

`status: off` hides the row. Labels are at most 24 characters. Numbers are measured by the
platform, so never write them in YAML.

The footer shows `<app name> v<N>`, the build commit and the deploy time. N goes up by one with
every push, so after `make wait` tell the user the new version number.

Examples are both the chips users click and the tests `make check` runs. Every screen needs at
least one. A file input in an example names a file in `data/`. `mock` is the answer the mock model
returns in `make check` and `make dev` with `LLM_MOCK=1`: write it as the ideal answer, in the
same shape as the blocks. A checklist `source` in a mock must be a passage the search really
finds; `make check` tells you if it is not.

## prompts/<name>.md

Jinja2, rendered with every input by name, every value `prepare(ctx)` returns, `site` and `app_name`.
An undefined name is an error, so use `{% if logs %}` for optional inputs. The platform adds the
system message, the JSON schema for the answer blocks and the knowledge passages as `[1] file — heading`
after your prompt. Say in the prompt what each block should contain and to cite passages by `[n]`.

## knowledge/

Markdown files split at headings; each section is one passage, found by its heading, its text and
its document's `# title`. Give each document one `# title` and short `##` sections. The 4 best
passages for the inputs are sent with the prompt and listed under the answer.
`knowledge:` must name a folder inside `app/`: an absolute path, `..`, or a symlink to anything
outside `app/` fails `make check`. Copy the documents in instead.

## hooks.py

```python
def prepare(ctx):
    rows = ctx.data("assets.csv")          # list of dicts from app/data/assets.csv
    text = ctx.text("policy.txt")          # a file from app/data/
    logs = ctx.inputs["logs"]              # every input, by name ("" when empty)
    return {"login_summary": "..."}        # new names for the prompt; not an input name
```

Use it for what the model should not guess: counts, lookups, dates, totals. Standard library only.
Errors name the line: `app/hooks.py line 12: KeyError: 'owner' (while running prepare(ctx))`.

## Recipes

- **Build an app from a brief:** app.yaml, one screen with the brief's inputs and a `text` answer,
  its prompt, the brief's synthetic data, two examples with mocks.
- **Ground it in documents:** add `knowledge/` files and `knowledge: knowledge/`; add a `checklist`
  and tell the prompt to cite `[n]`; update the mocks with real `[n]` from the search.
- **Shape the answer:** add `score`, `table` or `checklist` blocks, describe each in the prompt,
  update every example's mock to the new shape.
- **Exact numbers:** add `hooks.py` with `prepare(ctx)` and use its values in the prompt.
- **New screen:** add it to `screens:` in app.yaml, then its screen file and prompt.
- **Show the right status:** add `status:` with the chips that matter for the use case, renamed in
  the user's words (Reviews, Alerts triaged, Notes summarized).

## Not in this platform version

Workspace and assistant layouts, streamed answers, follow-up chat, charts, image input, download
and history. If a request needs one, say so and offer the closest block: a `table` instead of a
chart, a `checklist` the analyst can tick instead of history.
