# Build your app: lab guide

You build a working AI app by typing a few plain-language requests to an agentic harness. It
writes the app, checks it, and publishes it to your own app URL. You never edit code yourself,
and you don't need to know how.

The worked example is **Alert Triage**: a security analyst pastes an alert and its logs, and the
app returns a severity score, a verdict, the attack techniques and next steps from the security
team's own runbooks. Every part of it runs on-site, on the lab's own models.

Values in `<angle brackets>` come from your lab page.

## Before you start

- This is your own lab session: your own repo (`user-<N>`), app URL and agent. Nobody else's
  prompts change your app.
- You have: your lab user (`<user N>`) and the address of the harness on your VM (`<harness URL>`).
- Use only the made-up sample data in this repo. Never paste real alerts, logs, customer,
  patient or employee data.

## Step 0: check your app's system status

1. Open your app URL, `<your app URL>`, in a browser. If you don't have it yet,
   do step 1 below and ask the harness: *What is my app URL?*
2. You see **Mock App** and ten status tiles. Hover or tap the (i) on any tile to see what it
   means. The first three tell you the lab is ready:

   | Tile | Green means | If it is not green |
   |---|---|---|
   | App | The app is running; it shows its version and build | Wait a minute and refresh |
   | Fast model | The fast tier answered | Amber **Down**: tell the lab staff |
   | Smart model | The smart tier answered | Same as above |

   Grey **Mock mode** means the app is running without models, for rehearsals. The other tiles
   show why on-site AI matters: air-gapped, private data, $0 per token, data residency, speed
   under load and pinned model versions.
3. Press **Ask** on both models and **Run** on *10 requests at once*: you see the answer time,
   the tokens used and the cost, $0, measured on the lab's own GPUs.
4. Once your app has a screen, the **System status** link at the top right brings you back
   here; its dot turns amber when a model is down. The footer shows your app's version, which
   goes up by one with every push, so you can tell when a change is live.

![The system status page before the first prompt](guide-images/step-0-status.png)

## Step 1: open the harness

1. Open `<harness URL>` in your browser. It is already working in your repo, with the
   rules (`AGENTS.md`) and the how-to (`skills/base-app/SKILL.md`) loaded.
2. Start a new chat. Check it with: *Which folder may you edit, and what is my app URL?* It
   should answer `app/` and your app URL.

## Step 2: build the app (prompt 1)

Copy it from the lab guide, or type or paste:

```text
Build an alert triage app for our HQ security team. An analyst pastes an alert, can attach its
logs and pick the affected system, and gets a verdict on what happened. Make up sample alerts
and logs to try it with. Use the Alert Triage brief.
```

Your own words work too, for this prompt and the next two, as long as this first one names the
Alert Triage brief: the brief tells the harness the details you leave out.

The harness writes the app's files in `app/`, runs `make check`, pushes, waits for the new
build, and reports your app URL with timings. That takes a few minutes. Then:

1. Your app URL now opens **Triage an alert** instead of the system status page.
2. Click the example **Password spray, then a login**. You get a verdict.
3. Look under the answer: **Answered on-site in … s**, with the path from this device to the
   app to the smart model, all inside the site.

![After prompt 1: a verdict](guide-images/step-1-build.png)

## Step 3: ground it in your runbooks (prompt 2)

Copy it from the lab guide, or type or paste:

```text
Add our incident runbooks for password spray, phishing and malware, and give the analyst next
steps from them, each showing the runbook section it came from.
```

Refresh and click the same example. Now there is a **Next steps** checklist, each step with a
chip naming the runbook section it came from, and **Sources searched** under the answer.

![After prompt 2: next steps citing the runbooks](guide-images/step-2-ground.png)

## Step 4: shape the answer (prompt 3)

Copy it from the lab guide, or type or paste:

```text
Add a severity score from 0 to 100 and a table of the MITRE ATT&CK techniques. Count the failed
logins in the logs exactly instead of letting the AI guess. Add a harmless example too: a user
who got locked out and was already reset.
```

Refresh and try all three examples:

- **Password spray, then a login** scores high (80 or more).
- **Reported phishing email** scores in the middle.
- **Locked-out user, already reset** scores low (under 40).

The verdict now quotes exact counts, such as 212 failed logins for 9 accounts, because the app
counts them before the model answers.

![After prompt 3: severity, techniques and next steps](guide-images/step-3-shape.png)

## Or: build NetConf Guard or another use case

`catalog/` holds a brief for each guided use case. **NetConf Guard** (network operations) is
built the same way in three prompts: a network engineer pastes a switch, router or firewall
config and gets a risk score, the issues with exact fixes and the hardening rule each one breaks.
Its prompts are in `catalog/netconf-guard.md` and in the lab guide's use-case appendix.

1. Start a new harness chat and send prompt 1 from the brief. Your repo holds one app, so this
   replaces what you built. To keep it, start your message with *Add this as a second screen:*.
2. After each prompt, open your app, try a sample and check what the brief's table says to check.
3. The chips above the screen (Air-gapped, Configs stored, Reviews, Last review, Model, Standard)
   update after every review; hover one to see what it means.

For an idea with no brief, describe who uses it, what they paste or upload, and what they should
get back. The harness decides the details, so if an answer looks wrong, say what you expected.

## Step 5: make it yours

Send one change at a time, and check the app after each one. Ideas:

- *Call it SOC Triage and make it dark teal.*
- *Our data stays in the Frankfurt data center; show that.*
- *Analysts are in a hurry: make it answer faster.*
- *Add an example of a laptop calling out to an unknown address every five minutes.*
- *Add a second screen where I upload a day's firewall export and see the top talkers.*

To build your own idea instead, describe who uses it, what they paste or upload, and what they
should get back: *Build an app for store associates that checks a returns request against our
returns policy and says approve, refuse or escalate, with the policy section.* Every screen has
inputs on the left and an answer on the right made of text, a score, a table and a checklist.

Not available in this version: streamed answers, follow-up chat, charts, image input, and
download or history buttons. If you ask for one, the harness says so and offers the closest
thing that works, such as a table instead of a chart.

## Step 6: show what stays on-site

On any screen, point out:

- The chips above the screen: air-gapped, nothing stored, the run count at $0, the last answer
  time, the pinned model and its precision. Hover one to see what it means.
- **System status** at the top right: every tile, live, with the same reasons in more detail.
- The note under the inputs: what you enter stays in the site named in the app.
- The response route under each answer: measured time from this device to the model and back.

## If something goes wrong

| What you see | What to do |
|---|---|
| The harness says `make check` failed | Nothing: it reads the error and fixes it. If it fails three times, send: *Run make check and fix only what it names.* |
| The app URL still shows the old version | Wait a minute and refresh. Or send: *Run make wait and tell me when the new build is live.* |
| **That didn't run.** under the inputs | Read the message; send it to the harness: *The app says: "…". Fix it.* |
| **Mock answer: no model was called** under the answer | The app is in rehearsal mode; tell the lab staff if you expected the real models. |
| The harness wants to change files outside `app/` | Send: *Only edit app/.* The platform is read-only, and `make check` fails if it changes. |
| A change made things worse | Send: *Undo your last change and push again.* |

## What the harness does for you after each prompt

So you can follow along in its replies:

1. Writes or changes files in `app/` only.
2. `make check`: validates the app and runs every example against a stand-in model, in seconds.
3. `git push`: your repo builds a new app image and rolls it out.
4. `make wait`: waits until your app URL serves the new build.
5. `make smoke`: runs every example against the real models and reports the times.
