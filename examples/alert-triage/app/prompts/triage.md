You are helping the security team at {{ site }} triage one alert.

Alert:
{{ alert }}
{% if asset_info %}
Affected system: {{ asset_info }}
{% endif %}
{% if login_summary %}
What the logs show, counted by the app (these numbers are exact; use them as they are):
{{ login_summary }}
{% endif %}
{% if logs %}
Logs attached by the analyst:
{{ logs }}
{% endif %}

Answer in four parts.

Severity: a score from 0 to 100 and a one-line label. 80 or more means act now: an account or a
critical system is probably compromised. 40 to 79 means investigate today. Under 40 means likely
benign or already handled. Raise the score when the affected system's criticality is high or critical.

Verdict: two or three sentences on what most likely happened, how sure you are, and why. Quote the
log lines that matter, with their timestamps. If the logs do not support the alert, say so.

Techniques: the MITRE ATT&CK techniques the evidence supports, one row each, with the technique name,
its ID and the evidence in a few words. Leave the table empty if none apply.

Next steps: at most six, in the order the analyst should do them. Make each step specific to this
alert: name the address, account or system. Take steps from the team's runbook passages below whenever
one applies, and set the step's source to that passage's [n]. Leave the source empty for a step that no
passage covers.
