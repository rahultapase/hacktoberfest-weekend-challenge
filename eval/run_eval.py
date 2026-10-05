"""Run the synthetic eval set through each model, with and without the verifier.

    python eval/run_eval.py --models gemma4:e2b gemma3:1b

Writes eval/results/<model>.json (per line) and eval/results/results.md (tables + misses).
Run it with Wi-Fi off: the script records whether the internet was reachable.
"""

import argparse
import json
import platform
import socket
import statistics
import sys
import threading
import time
from datetime import date, datetime
from pathlib import Path

import httpx
import psutil

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

import metrics  # noqa: E402

from app import llm, names, parser, verifier  # noqa: E402

GOLD = ROOT / "eval" / "gold.jsonl"
ROSTER = ROOT / "eval" / "demo_roster.csv"
NICE = {"gemma4:e2b": "Gemma 4 E2B", "gemma3:1b": "Gemma 3 1B", "gemma3:4b": "Gemma 3 4B"}


def internet_reachable() -> bool:
    for host, port in (("1.1.1.1", 443), ("8.8.8.8", 53)):
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except OSError:
            pass
    return False


class RamSampler(threading.Thread):
    """Peak resident memory of all Ollama processes (server + model runner)."""

    def __init__(self):
        super().__init__(daemon=True)
        self.peak = 0
        self.stop_flag = threading.Event()

    def run(self):
        while not self.stop_flag.is_set():
            total = 0
            for p in psutil.process_iter(["name"]):
                try:
                    if "ollama" in (p.info["name"] or "").lower():
                        total += p.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            self.peak = max(self.peak, total)
            time.sleep(0.2)


def unload(model: str) -> None:
    try:
        httpx.post(f"{llm.OLLAMA_URL}/api/generate", json={"model": model, "keep_alive": 0}, timeout=60)
    except httpx.HTTPError:
        pass


def ollama_ps(model: str) -> dict:
    try:
        for m in httpx.get(f"{llm.OLLAMA_URL}/api/ps", timeout=5).json().get("models", []):
            if m.get("name") == model or m.get("model") == model:
                return {"size": m.get("size"), "size_vram": m.get("size_vram")}
    except (httpx.HTTPError, ValueError):
        pass
    return {}


def pct(xs, q):
    if not xs:
        return None
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def run_model(model: str, gold: list[dict], roster: list[dict], all_models: list[str]) -> dict:
    for m in all_models:
        unload(m)
    time.sleep(2)
    sampler = RamSampler()
    sampler.start()
    t0 = time.perf_counter()
    try:
        parser.parse_line("test line, ignore", model=model)
    except llm.LLMError as e:
        print("  warm-up failed:", e)
    cold = time.perf_counter() - t0
    ps = ollama_ps(model)
    print(f"  cold first call {cold:.1f}s, ollama ps: {ps}")

    lines, scores, lat = [], [], []
    for g in gold:
        entry = date.fromisoformat(g["entry_date"])
        err = None
        try:
            res = parser.parse_line(g["line"], entry, roster, model)
            events, secs = res["events"], res["seconds"]
        except llm.LLMError as e:
            events, secs, err = [], None, str(e)
        cards = verifier.verify(g["line"], entry, events, roster)
        sc = metrics.score_line(cards, g)
        scores.append(sc)
        if secs is not None:
            lat.append(secs)
        lines.append({
            "id": g["id"], "category": g["category"], "line": g["line"], "seconds": secs, "error": err,
            "events": events,
            "cards": [{k: c.get(k) for k in ("type", "student_text", "student_name", "status", "amount",
                                             "for_month", "on_date", "verdict")}
                      | {"reasons": [r["code"] for r in c.get("reasons", [])]} for c in cards],
            "score": {k: v for k, v in sc.items()},
        })
        flag = "" if sc["ver_silent"] == 0 else "  <-- SILENT"
        print(f"  #{g['id']:>2} {secs if secs is None else round(secs, 2)}s raw_silent={sc['raw_silent']} "
              f"ver_silent={sc['ver_silent']} green={sc['green']} amber={sc['amber']} miss={sc['missing_cards']}{flag}")
    sampler.stop_flag.set()
    sampler.join()

    agg = metrics.aggregate(scores, gold)
    agg.update({
        "model": model,
        "latency_p50": pct(lat, 0.5), "latency_p95": pct(lat, 0.95), "latency_mean": statistics.mean(lat) if lat else None,
        "cold_first_call_s": cold, "peak_ram_bytes": sampler.peak, "ollama_ps": ps,
        "errors": sum(1 for l in lines if l["error"]),
    })
    return {"summary": agg, "lines": lines}


def gb(b):
    return f"{b / 1024**3:.1f} GB" if b else "n/a"


def write_md(results: list[dict], meta: dict, out: Path) -> None:
    L = []
    L.append("# Eval results (synthetic set)\n")
    L.append(f"Run: {meta['started']} to {meta['finished']} (local time). Machine: {meta['machine']}. "
             f"Ollama {meta['ollama_version']}. **Internet reachable during run: {'yes' if meta['online'] else 'no (Wi-Fi off)'}**.\n")
    L.append(f"Test set: `eval/gold.jsonl`, **{meta['n_lines']} synthetic lines** written by the builder in the style of a "
             "home-tuition register (Hinglish, typos, WhatsApp-style messages). Labels written by hand from the spec rules, "
             "not by running a model. It is a sanity check, not a benchmark, and none of it is real student data.\n")
    L.append("## Headline\n")
    L.append("| Model | Fact precision | Fact recall | Silent errors (no verifier) | Silent errors (with verifier) | Sent to Confirm tray | Saved green and correct | p50 latency | p95 latency | Peak RAM (Ollama) |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in results:
        s = r["summary"]
        L.append(f"| {NICE.get(s['model'], s['model'])} | {s['precision']:.0%} | {s['recall']:.0%} | "
                 f"{s['silent_no_verifier']} of {s['pred_facts']} | {s['silent_with_verifier']} | "
                 f"{s['amber']} facts ({s['confirm_rate']:.0%}) + {s['missing_cards']} 'missed?' cards | "
                 f"{s['correct_saved_green']} of {s['gold_clean_facts']} | {s['latency_p50']:.1f} s | {s['latency_p95']:.1f} s | {gb(s['peak_ram_bytes'])} |")
    L.append("")
    L.append("Definitions: a **fact** is one (student, type, status/amount, month/date) entry. **Silent error** = a wrong fact "
             "that would be saved without anyone being asked. *No verifier* means every extracted fact is saved, with code "
             "still parsing amounts/dates and taking the closest roster name. *With verifier* means only green (V1 to V8 "
             "passed) facts are saved; amber ones wait in the Confirm tray. Lines marked `must_confirm` (two Nehas, an "
             "unknown student, a ₹15,000 payment) count as a silent error if saved green.\n")
    L.append("## Details\n")
    L.append("| | " + " | ".join(NICE.get(r["summary"]["model"], r["summary"]["model"]) for r in results) + " |")
    L.append("|---|" + "---:|" * len(results))
    rows = [
        ("Lines", "lines", "{}"), ("Gold facts", "gold_facts", "{}"), ("Facts extracted", "pred_facts", "{}"),
        ("Line exact match (no verifier)", "line_exact", "{:.0%}"),
        ("Lines fully auto-saved, all correct", "auto_complete_lines", "{}"),
        ("Tricky lines that should ask (caught)", None, None),
        ("Clean lines that still asked", None, None),
        ("Facts the model dropped", "drops", "{}"), ("...of which V7 flagged as 'missed?'", "drops_caught_v7", "{}"),
        ("Cold first call (model load)", "cold_first_call_s", "{:.0f} s"), ("Mean latency", "latency_mean", "{:.1f} s"),
        ("Errors / timeouts", "errors", "{}"),
    ]
    for label, key, fmt in rows:
        cells = []
        for r in results:
            s = r["summary"]
            if label.startswith("Tricky"):
                cells.append(f"{s['expect_confirm_caught']} of {s['expect_confirm_lines']}")
            elif label.startswith("Clean lines"):
                cells.append(f"{s['clean_lines_with_confirm']} of {s['clean_lines']}")
            else:
                cells.append(fmt.format(s[key]) if s[key] is not None else "n/a")
        L.append(f"| {label} | " + " | ".join(cells) + " |")
    L.append("\nPeak RAM = peak resident memory of all Ollama processes (server + runner), sampled every 0.2 s with psutil. "
             "GPU memory is not included. Latency is per line, warm (model already loaded), measured around the HTTP call.")
    L.append("")

    for r in results:
        name = NICE.get(r["summary"]["model"], r["summary"]["model"])
        L.append(f"## {name}: what went wrong\n")
        sil = [l for l in r["lines"] if l["score"]["ver_silent"]]
        L.append(f"**Silent errors that got past the verifier ({len(sil)} lines):**\n")
        for l in sil:
            L.append(f"- #{l['id']} `{l['line']}` → saved {json.dumps(l['score']['silent_ver_facts'], ensure_ascii=False)}")
        if not sil:
            L.append("- none")
        caught = [l for l in r["lines"] if l["score"]["raw_silent"] and not l["score"]["ver_silent"]]
        L.append(f"\n**Wrong without the verifier, stopped by it ({len(caught)} lines):**\n")
        for l in caught[:12]:
            reasons = sorted({c for card in l["cards"] for c in card["reasons"]})
            L.append(f"- #{l['id']} `{l['line']}` → would have saved {json.dumps(l['score']['silent_raw_facts'], ensure_ascii=False)}; flagged by {', '.join(reasons) or '-'}")
        if len(caught) > 12:
            L.append(f"- … {len(caught) - 12} more in `{r['summary']['model'].replace(':', '_')}.json`")
        drops = [l for l in r["lines"] if l["score"]["drops"]]
        L.append(f"\n**Lines where a fact was missing ({len(drops)}):**\n")
        for l in drops[:12]:
            L.append(f"- #{l['id']} `{l['line']}`: missing {json.dumps(l['score']['dropped_facts'], ensure_ascii=False)}"
                     f"{' (V7 flagged)' if l['score']['drops_caught'] else ''}")
        if len(drops) > 12:
            L.append(f"- … {len(drops) - 12} more")
        L.append("")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["gemma4:e2b", "gemma3:1b"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default=str(ROOT / "eval" / "results"))
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    gold = [json.loads(l) for l in GOLD.read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.limit:
        gold = gold[: args.limit]
    roster = names.load_roster_csv(ROSTER)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    online = internet_reachable()
    try:
        ver = httpx.get(f"{llm.OLLAMA_URL}/api/version", timeout=5).json().get("version")
    except httpx.HTTPError:
        ver = "?"
    meta = {"started": datetime.now().isoformat(timespec="seconds"), "online": online, "n_lines": len(gold),
            "ollama_version": ver,
            "machine": f"{platform.system()} {platform.release()}, {psutil.cpu_count()} CPU threads, "
                       f"{psutil.virtual_memory().total / 1024**3:.0f} GB RAM, RTX 2050 4 GB"}
    print(f"internet reachable: {online}  lines: {len(gold)}  ollama {ver}")

    results = []
    for m in args.models:
        print(f"== {m}")
        r = run_model(m, gold, roster, args.models)
        r["meta"] = meta
        (out / f"{m.replace(':', '_')}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        results.append(r)
        s = r["summary"]
        print(f"   precision {s['precision']:.0%} recall {s['recall']:.0%} silent raw {s['silent_no_verifier']} "
              f"silent ver {s['silent_with_verifier']} amber {s['amber']} p50 {s['latency_p50']:.2f}s")
    meta["finished"] = datetime.now().isoformat(timespec="seconds")
    meta["online_at_end"] = internet_reachable()
    if not args.limit:
        write_md(results, meta, out / "results.md")
    else:
        write_md(results, meta, out / "results_dev.md")
    print("done")


if __name__ == "__main__":
    main()
