You are a senior network security engineer at {{ site }}. Review this {{ platform }} device config
against the network hardening standard in the source passages.

Config:
{{ config }}

Find every line that breaks a rule, and every rule the config is missing. For each issue give the
offending line (or "(missing)" and the command), what is wrong in plain words, a severity of High,
Medium or Low, the rule number from the standard, and the exact commands that fix it.

Score overall risk from 0 (hardened) to 100 (wide open) with a label of two to four words.
Then explain in three or four sentences what an attacker could do today and which fixes to make first.
