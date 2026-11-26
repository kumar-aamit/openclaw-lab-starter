# Runbook: password spray against VPN or single sign-on

## Signs
Many failed logins from one source address, spread across many accounts with only a few tries each,
so no single account locks out. A successful login from the same source after the failures means
an account is probably compromised.

## Contain
Block the source address at the VPN gateway and the firewall edge. Disable the VPN session of any
account that logged in successfully from that address, and force a password reset for it.
Turn off legacy VPN clients that skip multi-factor authentication.

## Investigate
List every account the source tried. For accounts that logged in, pull the VPN session log and check
which internal systems the session reached and how much data it sent. Check sign-in logs for the same
accounts from other addresses in the last 7 days.

## Escalate
Call the on-call incident lead if a compromised session reached a critical system, such as a domain
controller or the finance database. Open an incident ticket with the source address, the accounts and
the session details.
