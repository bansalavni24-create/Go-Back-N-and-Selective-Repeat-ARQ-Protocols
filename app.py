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
    results = []
    for name in PROTOCOLS:
        modulo = pick_modulo(name, scheme, window)
        r = run_protocol(name, message, window, modulo, delay=delay, timeout=timeout,
                         every_kth=every_kth, ack_every_kth=ack_kth,
                         max_ticks=300 + 30 * len(message))
        r["protocol"] = name
        r["modulo"] = modulo
        results.append(r)
    return jsonify({"message": message, "window": window, "results": results})


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


@app.route("/api/graphs")
def api_graphs():
    runs = 20

    def avg(protocol, total, window, loss):
        vals = []
        for _ in range(runs):
            t, _sent = protocol(total, window, loss)
            vals.append(total / t)
        return sum(vals) / len(vals)

    losses = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    windows = [1, 2, 4, 8, 16, 32]
    delay, timeout = 5, 12

    def th_sw(p):
        q = (1 - p) ** 2
        return 1 / (2 * delay + (1 - q) / q * timeout)

    return jsonify({
        "losses": [l * 100 for l in losses],
        "loss_gbn": [avg(go_back_n, 100, 8, l) for l in losses],
        "loss_sr": [avg(selective_repeat, 100, 8, l) for l in losses],
        "windows": windows,
        "win_gbn": [avg(go_back_n, 100, w, 0.10) for w in windows],
        "win_sr": [avg(selective_repeat, 100, w, 0.10) for w in windows],
        "theory_losses": [l * 100 for l in losses],
        "sim_sw": [avg(go_back_n, 300, 1, l) for l in losses],
        "th_sw": [th_sw(l) for l in losses],
        "sim_sr": [avg(selective_repeat, 300, 32, l) for l in losses],
        "th_sr": [(1 - l) ** 2 for l in losses],
    })


if __name__ == "__main__":
    print("Open http://127.0.0.1:5000 in your browser. Press Ctrl+C here to stop.")
    app.run(debug=False)