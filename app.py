import io
from contextlib import redirect_stdout

from flask import Flask, jsonify, render_template, request

from stopwait import run_stop_and_wait
from gbn import run_go_back_n, go_back_n
from sr import run_selective_repeat, selective_repeat
import numbering

app = Flask(__name__)

PROTOCOLS = ["Stop-and-Wait", "Go-Back-N", "Selective Repeat"]


def to_int(value, default, low, high):
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return default


def run_protocol(name, message, window, modulo, **settings):
    """Run one protocol and also capture the step-by-step log."""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        if name == "Stop-and-Wait":
            r = run_stop_and_wait(message, modulo=modulo, log=True, **settings)
        elif name == "Go-Back-N":
            r = run_go_back_n(message, window, modulo=modulo, log=True, **settings)
        else:
            r = run_selective_repeat(message, window, modulo=modulo, log=True, **settings)
    r["log"] = buffer.getvalue().splitlines()
    return r


def pick_modulo(name, scheme, window):
    if scheme == "not_told":
        return None
    if scheme == "mod1":
        return 1
    if scheme == "mod2":
        return 2
    # "safe": the smallest modulo that is always enough
    if name == "Stop-and-Wait":
        return 2
    if name == "Go-Back-N":
        return window + 1
    return 2 * window


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/demo", methods=["POST"])
def api_demo():
    data = request.get_json(force=True)
    message = (data.get("message") or "NETWORKS").strip()[:20] or "NETWORKS"
    window = to_int(data.get("window"), 3, 1, 8)
    every_kth = to_int(data.get("every_kth"), 4, 0, 20)
    ack_kth = to_int(data.get("ack_every_kth"), 0, 0, 20)
    delay = to_int(data.get("delay"), 2, 1, 10)
    timeout = to_int(data.get("timeout"), 6, 2, 40)
    scheme = data.get("scheme", "safe")
    random_loss = to_int(data.get("random_loss"), 0, 0, 60) / 100
    results = []
    for name in PROTOCOLS:
        modulo = pick_modulo(name, scheme, window)
        r = run_protocol(name, message, window, modulo, delay=delay, timeout=timeout,
                         every_kth=0 if random_loss > 0 else every_kth,
                         ack_every_kth=0 if random_loss > 0 else ack_kth,
                         loss_prob=random_loss, max_ticks=300 + 30 * len(message))
        if isinstance(r["delivered"], str) and len(r["delivered"]) > 40:
            r["delivered"] = r["delivered"][:40] + "..."
        r["protocol"] = name
        r["modulo"] = modulo
        results.append(r)
    return jsonify({"message": message, "window": window, "delay": delay, "timeout": timeout, "random_loss": int(round(random_loss * 100)), "every_kth": every_kth, "results": results})


@app.route("/api/numbering", methods=["POST"])
def api_numbering():
    data = request.get_json(force=True)
    message = (data.get("message") or "NETWORKS").strip()[:20] or "NETWORKS"
    out = {"message": message, "window": numbering.WINDOW,
           "every_kth": numbering.EVERY_KTH, "ack_every_kth": numbering.ACK_EVERY_KTH}

    def cell(r):
        return {"status": numbering.status(r), "sent": r["sent"] if r["finished"] else None,
                "got": r["delivered"] if r["finished"] else r["delivered"][:12] + "..."}

    schemes = [{"name": "Modulo-2 (0,1,0,1...)", "modulo": 2},
               {"name": "Not told (0,1,2,3...)", "modulo": None},
               {"name": "Modulo-1 (0,0,0,0...)", "modulo": 1}]
    for key, ack in (("frames_only", 0), ("frames_and_acks", numbering.ACK_EVERY_KTH)):
        out[key] = [{"name": s["name"],
                     "cells": [cell(numbering.run(p, message, s["modulo"], numbering.EVERY_KTH, ack))
                               for p in PROTOCOLS]} for s in schemes]

    out["modulo_table"] = []
    for p in PROTOCOLS:
        row = []
        for m in range(1, 9):
            r = numbering.run(p, message, m, numbering.EVERY_KTH, numbering.ACK_EVERY_KTH)
            row.append("stuck" if not r["finished"] else ("ok" if r["correct"] else "bad"))
        out["modulo_table"].append({"protocol": p, "cells": row})
    out["safe"] = [2, numbering.WINDOW + 1, 2 * numbering.WINDOW]

    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    sizes, losses = [4, 6, 8, 10, 12, 16, 20], [3, 4, 5, 6, 8]
    out["sweep_total"] = len(sizes) * len(losses)
    for key, ack in (("sweep_frames_only", 0), ("sweep_frames_and_acks", numbering.ACK_EVERY_KTH)):
        rows = []
        for s in schemes:
            cells = []
            for p in PROTOCOLS:
                good = stuck = 0
                for n in sizes:
                    for k in losses:
                        r = numbering.run(p, letters[:n], s["modulo"], k, ack)
                        if not r["finished"]:
                            stuck += 1
                        elif r["correct"]:
                            good += 1
                cells.append({"good": good, "stuck": stuck})
            rows.append({"name": s["name"], "cells": cells})
        out[key] = rows
    return jsonify(out)


@app.route("/api/graphs", methods=["GET", "POST"])
def api_graphs():
    data = request.get_json(silent=True) or {}
    window = to_int(data.get("window"), 8, 1, 64)
    delay = to_int(data.get("delay"), 5, 1, 20)
    timeout = to_int(data.get("timeout"), 12, 2, 60)
    packets = to_int(data.get("packets"), 100, 20, 500)
    runs = to_int(data.get("runs"), 20, 5, 100)
    window_loss = to_int(data.get("window_loss"), 10, 0, 50) / 100

    def avg(protocol, w, loss):
        """Average throughput and average frames sent per packet over many runs."""
        thr, over = [], []
        for _ in range(runs):
            t, sent = protocol(packets, w, loss, delay, timeout)
            thr.append(packets / t)
            over.append(sent / packets)
        return sum(thr) / runs, sum(over) / runs

    losses = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    windows = sorted(set([1, 2, 4, 8, 16, 32] + [window]))

    def th_sw(p):
        q = (1 - p) ** 2
        return 1 / (2 * delay + (1 - q) / q * timeout)

    sw = [avg(go_back_n, 1, l) for l in losses]
    gbn = [avg(go_back_n, window, l) for l in losses]
    sr = [avg(selective_repeat, window, l) for l in losses]
    wg = [avg(go_back_n, w, window_loss) for w in windows]
    ws = [avg(selective_repeat, w, window_loss) for w in windows]
    return jsonify({
        "params": {"window": window, "delay": delay, "timeout": timeout, "packets": packets,
                   "runs": runs, "window_loss": int(round(window_loss * 100)), "bdp": 2 * delay + 1},
        "warning": "" if timeout > 2 * delay else "Timeout is not larger than 2 x delay, so frames are resent too early and every protocol slows down.",
        "losses": [int(round(l * 100)) for l in losses],
        "loss_sw": [x[0] for x in sw], "loss_gbn": [x[0] for x in gbn], "loss_sr": [x[0] for x in sr],
        "over_sw": [x[1] for x in sw], "over_gbn": [x[1] for x in gbn], "over_sr": [x[1] for x in sr],
        "over_th": [1 / (1 - l) ** 2 for l in losses],
        "windows": windows,
        "win_gbn": [x[0] for x in wg], "win_sr": [x[0] for x in ws],
        "th_sw": [th_sw(l) for l in losses],
        "th_sr": [(1 - l) ** 2 for l in losses],
    })


if __name__ == "__main__":
    print("Open http://127.0.0.1:5000 in your browser. Press Ctrl+C here to stop.")
    app.run(debug=False)