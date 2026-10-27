import io
from contextlib import redirect_stdout

from flask import Flask, jsonify, render_template, request

from stopwait import run_stop_and_wait
from gbn import run_go_back_n, go_back_n
from sr import run_selective_repeat, selective_repeat
import numbering

app = Flask(__name__)

PROTOCOLS = ["Stop-and-Wait", "Go-Back-N", "Selective Repeat"]


LIMITS = {
    "demo": {"message": [1, 20], "window": [1, 8], "every_kth": [2, 20], "ack_every_kth": [2, 20],
             "random_loss": [0, 60], "delay": [1, 10], "timeout": [2, 40]},
    "graphs": {"window": [1, 64], "delay": [1, 20], "timeout": [2, 60], "packets": [20, 500],
               "runs": [5, 100], "window_loss": [0, 50]},
    "reallife": {"window": [1, 64], "loss": [0, 30]},
}


def read_int(data, key, label, low, high, default, errors, zero_ok=False):
    """Read a whole number inside its limits, or record a clear error message."""
    raw = data.get(key, default)
    try:
        if isinstance(raw, bool):
            raise ValueError
        n = int(str(raw).strip())
    except ValueError:
        errors.append(f"{label} must be a whole number")
        return default
    if zero_ok and n == 0:
        return 0
    if n < low or n > high:
        errors.append(f"{label} must be " + ("0 or " if zero_ok else "") + f"between {low} and {high}")
        return default
    return n


def check_timeout(delay, timeout, errors):
    if timeout <= 2 * delay and not errors:
        errors.append(f"Timeout must be more than 2 x delay (at least {2 * delay + 1} for delay {delay})")


def bad_request(errors):
    return jsonify({"errors": errors}), 400


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


@app.route("/api/limits")
def api_limits():
    return jsonify(LIMITS)


@app.route("/api/demo", methods=["POST"])
def api_demo():
    data = request.get_json(force=True)
    L = LIMITS["demo"]
    errors = []
    message = (data.get("message") or "").strip()
    if not (L["message"][0] <= len(message) <= L["message"][1]):
        errors.append(f"Message must be {L['message'][0]} to {L['message'][1]} letters")
        message = "NETWORKS"
    window = read_int(data, "window", "Window size", *L["window"], 3, errors)
    every_kth = read_int(data, "every_kth", "Every k-th frame lost", *L["every_kth"], 4, errors, zero_ok=True)
    ack_kth = read_int(data, "ack_every_kth", "Every k-th ACK lost", *L["ack_every_kth"], 0, errors, zero_ok=True)
    random_loss = read_int(data, "random_loss", "Random loss %", *L["random_loss"], 0, errors) / 100
    delay = read_int(data, "delay", "Delay", *L["delay"], 2, errors)
    timeout = read_int(data, "timeout", "Timeout", *L["timeout"], 6, errors)
    check_timeout(delay, timeout, errors)
    scheme = data.get("scheme", "safe")
    if scheme not in ("safe", "mod2", "not_told", "mod1"):
        errors.append("Unknown sequence-number choice")
    if errors:
        return bad_request(errors)
    results = []
    for name in PROTOCOLS:
        modulo = pick_modulo(name, scheme, window)
        r = run_protocol(name, message, window, modulo, delay=delay, timeout=timeout,
                         every_kth=0 if random_loss > 0 else every_kth,
                         ack_every_kth=0 if random_loss > 0 else ack_kth,
                         loss_prob=random_loss, max_ticks=300 + 30 * len(message))
        r["protocol"] = name
        r["modulo"] = modulo
        results.append(r)
    return jsonify({"message": message, "window": window, "delay": delay, "timeout": timeout,
                    "random_loss": int(round(random_loss * 100)), "every_kth": every_kth, "results": results})


@app.route("/api/numbering", methods=["POST"])
def api_numbering():
    data = request.get_json(force=True)
    message = (data.get("message") or "").strip()
    if not 1 <= len(message) <= 20:
        return bad_request(["Message must be 1 to 20 letters"])
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
    L = LIMITS["graphs"]
    errors = []
    window = read_int(data, "window", "Window size", *L["window"], 8, errors)
    delay = read_int(data, "delay", "Delay", *L["delay"], 5, errors)
    timeout = read_int(data, "timeout", "Timeout", *L["timeout"], 12, errors)
    packets = read_int(data, "packets", "Packets sent", *L["packets"], 100, errors)
    runs = read_int(data, "runs", "Runs per point", *L["runs"], 20, errors)
    window_loss = read_int(data, "window_loss", "Loss for window graph", *L["window_loss"], 10, errors) / 100
    check_timeout(delay, timeout, errors)
    if errors:
        return bad_request(errors)

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
        "warning": "",
        "losses": [int(round(l * 100)) for l in losses],
        "loss_sw": [x[0] for x in sw], "loss_gbn": [x[0] for x in gbn], "loss_sr": [x[0] for x in sr],
        "over_sw": [x[1] for x in sw], "over_gbn": [x[1] for x in gbn], "over_sr": [x[1] for x in sr],
        "over_th": [1 / (1 - l) ** 2 for l in losses],
        "windows": windows,
        "win_gbn": [x[0] for x in wg], "win_sr": [x[0] for x in ws],
        "th_sw": [th_sw(l) for l in losses],
        "th_sr": [(1 - l) ** 2 for l in losses],
    })


SCENARIOS = [
    {"id": "train-radio", "name": "Railway: train to control centre (radio link)", "tick_ms": 5, "delay": 20, "timeout": 50,
     "messages": 100, "max_loss": 20, "typical_loss": 5, "window": 8,
     "story": "A moving train sends position and brake-status messages to the control centre over a radio link. Tunnels and cell hand-overs drop messages, and every message must arrive in order.",
     "what": "100 status messages"},
    {"id": "station-lan", "name": "Railway: station ticket counters (wired LAN)", "tick_ms": 1, "delay": 1, "timeout": 4,
     "messages": 100, "max_loss": 5, "typical_loss": 1, "window": 4,
     "story": "Booking terminals send requests to the station server over a wired network. Delay and loss are tiny here, so the choice of protocol should matter very little.",
     "what": "100 booking requests"},
    {"id": "airport-wifi", "name": "Airport: baggage and flight-info updates (busy Wi-Fi)", "tick_ms": 1, "delay": 10, "timeout": 30,
     "messages": 100, "max_loss": 20, "typical_loss": 10, "window": 8,
     "story": "Baggage scanners and flight boards send updates over a crowded terminal Wi-Fi. Many devices share the air, so frames are lost often but the delay is short.",
     "what": "100 baggage or flight updates"},
    {"id": "air-ground", "name": "Airport: aircraft to ground link (satellite)", "tick_ms": 10, "delay": 30, "timeout": 70,
     "messages": 100, "max_loss": 10, "typical_loss": 3, "window": 16,
     "story": "An aircraft sends flight data to the ground through a satellite. One trip takes a long time, so waiting for an ACK after every message wastes the link.",
     "what": "100 flight-data messages"},
]


@app.route("/api/scenarios")
def api_scenarios():
    return jsonify(SCENARIOS)


@app.route("/api/reallife", methods=["POST"])
def api_reallife():
    data = request.get_json(silent=True) or {}
    sc = next((s for s in SCENARIOS if s["id"] == data.get("scenario")), None)
    if sc is None:
        return bad_request(["Pick a scenario"])
    L = LIMITS["reallife"]
    errors = []
    window = read_int(data, "window", "Window size", *L["window"], sc["window"], errors)
    typical = read_int(data, "loss", "Typical loss", 0, sc["max_loss"], sc["typical_loss"], errors)
    if errors:
        return bad_request(errors)
    runs, n = 15, sc["messages"]

    def avg(protocol, w, loss):
        times, sent = [], []
        for _ in range(runs):
            t, s = protocol(n, w, loss, sc["delay"], sc["timeout"])
            times.append(t * sc["tick_ms"] / 1000)
            sent.append(s / n)
        return sum(times) / runs, sum(sent) / runs

    protos = [("sw", go_back_n, 1), ("gbn", go_back_n, window), ("sr", selective_repeat, window)]
    grid = [round(sc["max_loss"] * i / 6, 1) for i in range(7)]
    out = {"scenario": sc, "window": window, "typical_loss": typical, "losses": grid, "runs": runs}
    for key, proto, w in protos:
        pts = [avg(proto, w, g / 100) for g in grid]
        out["time_" + key] = [p[0] for p in pts]
        out["over_" + key] = [p[1] for p in pts]
        t, s = avg(proto, w, typical / 100)
        out["typical_" + key] = {"seconds": t, "frames_per_message": s}
    return jsonify(out)


if __name__ == "__main__":
    print("Open http://127.0.0.1:5000 in your browser. Press Ctrl+C here to stop.")
    app.run(debug=False)