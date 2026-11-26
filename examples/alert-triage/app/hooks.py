"""Count what the logs show before the model reads them, so the numbers in the answer are exact."""
import re
from collections import Counter

LOGIN = re.compile(r"^(?P<time>\S+) \S+ auth user=(?P<user>\S+) src=(?P<src>\S+) result=(?P<result>OK|FAIL)(?P<rest>.*)$")


def summarize_logins(text):
    rows = [m.groupdict() for m in map(LOGIN.match, text.splitlines()) if m]
    if not rows:
        return ""
    failed = [r for r in rows if r["result"] == "FAIL"]
    if not failed:
        return f"{len(rows)} logins, none failed."
    sources = Counter(r["src"] for r in failed)
    users = sorted({r["user"] for r in failed})
    first, last = failed[0]["time"], failed[-1]["time"]
    lines = [
        f"{len(failed)} failed logins from {first} to {last}.",
        f"Accounts tried: {len(users)} ({', '.join(users)}).",
        "Failures by source: " + ", ".join(f"{src} ({n})" for src, n in sources.most_common(5)) + ".",
    ]
    for r in rows:
        if r["result"] == "OK" and r["src"] in sources and r["user"] in users and r["time"] > first:
            lines.append(f"Success after failures: {r['user']} from {r['src']} at {r['time']}{r['rest']}.")
    return "\n".join(lines)


def describe_asset(ctx, hostname):
    for row in ctx.data("assets.csv"):
        if row["hostname"] == hostname:
            return f"{hostname}: {row['role']}, owned by {row['owner']}, criticality {row['criticality']}"
    return ""


def prepare(ctx):
    return {
        "login_summary": summarize_logins(ctx.inputs["logs"]),
        "asset_info": describe_asset(ctx, ctx.inputs["asset"]) if ctx.inputs["asset"] else "",
    }
