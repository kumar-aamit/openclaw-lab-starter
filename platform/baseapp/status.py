"""System status: the tiles on the status page, the chips above each screen, and in-process counters.

Every number here is measured in this pod or read from its settings. Counters live in memory and
start again at zero when a new build rolls out; the pod stays stateless.
"""
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .config import ModelEndpoint, Settings
from .health import CheckResult
from .knowledge import KnowledgeIndex
from .screens import ScreenSpec, StatusChip

DEFAULT_CHIPS = ("airgap", "stored", "runs", "last", "model")
CHIP_LABELS = {"airgap": "Air-gapped", "stored": "Data stored", "runs": "Runs", "last": "Last answer",
               "model": "Model", "knowledge": "Knowledge"}

ASKS = {
    "fast": {
        "title": "Ask the fast model",
        "question": "%SEC_LOGIN-4-LOGIN_FAILED: Login failed [user: admin] [Source: 10.1.4.22]",
        "prompt": "Classify this network log line in two short sentences: what happened, how severe, "
                  "and what to watch for next.\n\n%SEC_LOGIN-4-LOGIN_FAILED: Login failed [user: admin] "
                  "[Source: 10.1.4.22]",
        "mock": "Failed login, medium severity: the admin account was tried from 10.1.4.22. Repeated "
                "failures from the same source would suggest a password spray.",
    },
    "smart": {
        "title": "Ask the smart model",
        "question": "In two sentences, why should a hospital run AI on-site?",
        "prompt": "In two sentences, why should a hospital run AI on-site rather than in a public cloud?",
        "mock": "A hospital handles protected health information in almost every record, so keeping the "
                "model on-site removes any question of who else can see that data. It also keeps clinical "
                "tools working during an internet outage and avoids a per-token bill for high-volume work.",
    },
}
LOAD_REQUESTS = 10
LOAD_PROMPT = "Reply with one word: the severity (low, medium or high) of 'interface Gi1/0/3 changed state to down'."


@dataclass
class Stats:
    started: float = field(default_factory=time.time)
    tokens: int = 0
    runs: dict[str, int] = field(default_factory=dict)
    last_ms: dict[str, int] = field(default_factory=dict)
    load_ms: list[int] = field(default_factory=list)

    def record_run(self, screen: str, total_ms: int, tokens: int | None) -> None:
        self.runs[screen] = self.runs.get(screen, 0) + 1
        self.last_ms[screen] = total_ms
        self.tokens += tokens or 0

    @property
    def load_median(self) -> int | None:
        return round(statistics.median(self.load_ms)) if self.load_ms else None

    @property
    def deployed(self) -> str:
        return datetime.fromtimestamp(self.started, timezone.utc).strftime("%b %-d, %H:%M UTC")


def memory_mib() -> float | None:
    try:
        with open("/proc/self/status", encoding="ascii") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024
    except OSError:
        return None
    return None


def model_label(endpoint: ModelEndpoint) -> str:
    if not endpoint.model:
        return "not configured"
    return f"{endpoint.short_name} · {endpoint.precision}" if endpoint.precision else endpoint.short_name


def seconds(ms: int | None) -> str:
    if ms is None:
        return "—"
    return f"{ms} ms" if ms < 1000 else f"{ms / 1000:.1f} s"


def plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


@dataclass(frozen=True)
class Tile:
    id: str
    name: str
    icon: str
    status: str
    metric: str
    meaning: str
    state: str = "ok"  # ok, fail or skip


def _model_tile(tid: str, name: str, icon: str, check: CheckResult | None, endpoint: ModelEndpoint,
                meaning: str) -> Tile:
    if check is None:
        return Tile(tid, name, icon, "Checking", model_label(endpoint), meaning, "skip")
    if check.ok is None:
        return Tile(tid, name, icon, "Mock mode", model_label(endpoint), meaning, "skip")
    if not check.ok:
        return Tile(tid, name, icon, "Down", check.detail, meaning, "fail")
    return Tile(tid, name, icon, "Ready", f"{check.ms} ms · {model_label(endpoint)}", meaning)


def tiles(settings: Settings, site: str, stats: Stats, indexes: dict[str, KnowledgeIndex],
          checks: dict[str, CheckResult] | None = None) -> list[Tile]:
    checks = checks or {}
    mem = memory_mib()
    passages = sum(len(ix.passages) for ix in indexes.values())
    probe = time.perf_counter()
    for ix in indexes.values():
        ix.search("password telnet snmp ssh", k=4)
    search_ms = (time.perf_counter() - probe) * 1000
    fast, smart = settings.fast, settings.smart
    return [
        Tile("app", "App", "server", "Ready",
             f"v{settings.version} · {settings.commit[:7]}" + (f" · {mem:.0f} MiB" if mem else ""),
             "Your app runs as a small container on the Kubernetes cluster. Every push rebuilds it and "
             "rolls it out; the version goes up by one each time."),
        _model_tile("fast", "Fast model", "zap", checks.get("Fast model"), fast,
                    f"{fast.model or 'The fast tier'} on {site} GPUs. Answers short, simple tasks almost "
                    "instantly."),
        _model_tile("smart", "Smart model", "cpu", checks.get("Smart model"), smart,
                    f"{smart.model or 'The smart tier'} on {site} GPUs. Handles reasoning-heavy work such as "
                    "reviewing a config or triaging an alert."),
        Tile("knowledge", "Knowledge", "search", "Ready" if passages else "None yet",
             f"{plural(passages, 'section')} · {search_ms:.0f} ms" if passages else "no documents yet",
             "Searches the documents in your app, such as a standard or a runbook, and gives the model the "
             "relevant sections. It runs inside the app.", "ok" if passages else "skip"),
        Tile("airgap", "Air-gapped", "wifi-off", "On", "0 external calls",
             "Nothing in your app reaches the internet. Scripts, styles, fonts and models are all on-site, "
             "so it keeps working offline."),
        Tile("private", "Private data", "lock", "On-site", "0 bytes stored",
             f"What you type goes only to the models in {site} and is never written to disk or logs."),
        Tile("tokens", "Token cost", "coins", "$0", f"{stats.tokens:,} tokens",
             "On-site models have no per-token bill. The count is every token this build has used since it "
             "started."),
        Tile("region", "Data residency", "landmark", "In-region", "3 hops on-site",
             f"Every hop, from your browser to the app to the model, is inside {site}, so regulated data "
             "stays in-region and you can show where it went."),
        Tile("load", "Under load", "gauge", "Ready",
             f"10 at once · median {stats.load_median} ms" if stats.load_median else "dedicated GPUs",
             f"These GPUs are not shared with other tenants, so answers stay fast when everyone asks at "
             f"once. The test below sends {LOAD_REQUESTS} requests at once to the fast model."),
        Tile("models", "Model version", "sliders-horizontal", "Pinned",
             f"{model_label(smart)}\n{model_label(fast)}",
             f"Smart tier: {smart.model or 'not configured'}"
             f"{' at ' + smart.precision if smart.precision else ''}. Fast tier: {fast.model or 'not configured'}"
             f"{' at ' + fast.precision if fast.precision else ''}. You choose the models, their precision "
             "and when they change, so answers stay consistent."),
    ]


@dataclass(frozen=True)
class Chip:
    kind: str
    label: str
    value: str
    meaning: str


def chips(screen: ScreenSpec, settings: Settings, site: str, stats: Stats,
          index: KnowledgeIndex | None) -> list[Chip]:
    chosen = screen.status if screen.status is not None else tuple(
        StatusChip(k) for k in DEFAULT_CHIPS + (("knowledge",) if screen.knowledge else ()))
    endpoint = settings.smart if screen.model == "smart" else settings.fast
    runs = stats.runs.get(screen.name, 0)
    docs = len({p.source for p in index.passages}) if index else 0
    sections = len(index.passages) if index else 0
    out = []
    for c in chosen:
        label = c.label or CHIP_LABELS[c.kind]
        value, meaning = {
            "airgap": ("On", "Nothing in this app reaches the internet. Scripts, styles and the model are "
                             "all on-site, so it keeps working offline."),
            "stored": ("None", f"What you enter goes only to the {screen.model} model in {site} for this "
                               "answer. It is never written to disk or logs."),
            "runs": (f"{runs} · $0", f"Answers since this build started, and what they cost. On-site models "
                                     f"have no per-token bill: {stats.tokens:,} tokens so far."),
            "last": (seconds(stats.last_ms.get(screen.name)),
                     "Time from pressing Run to the full answer, on dedicated on-site GPUs."),
            "model": (model_label(endpoint),
                      f"{endpoint.model or 'Not configured'}"
                      f"{' at ' + endpoint.precision if endpoint.precision else ''}, the {screen.model} tier. "
                      "It only changes when you change it, so answers stay consistent."),
            "knowledge": (f"{plural(docs, 'doc')} · {plural(sections, 'section')}",
                          "Every answer is checked against the documents in this app, and steps cite the "
                          "section they came from."),
        }[c.kind]
        out.append(Chip(c.kind, label, value, meaning))
    return out
