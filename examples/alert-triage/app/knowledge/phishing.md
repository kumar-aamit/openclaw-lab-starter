# Runbook: reported phishing email

## Signs
A sender domain that imitates ours or a supplier's, urgency, and a request to sign in, pay, or confirm
bank or payroll details through a link or an attachment.

## Contain
Pull every copy of the email from mailboxes with the mail relay's search-and-purge, using the sender
and the subject. Block the sender domain and any link domains at the mail relay and the web proxy.

## Investigate
Search the web proxy log for anyone who opened the link, and the sign-in logs for logins by those people
after they opened it. Ask the reporter whether they replied or entered anything.

## Recover
Reset the password and revoke the sessions of anyone who entered credentials. If bank or payroll details
were changed, call payroll to freeze the change. Thank the reporter.
