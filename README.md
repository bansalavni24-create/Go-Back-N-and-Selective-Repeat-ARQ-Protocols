# Performance Analysis of Go-Back-N and Selective Repeat ARQ Protocols

Computer Networks individual project, VIT. By Avni Bansal.

A Python simulator that sends a message through a lossy channel using **Stop-and-Wait**, **Go-Back-N** and **Selective Repeat**, then compares how fast they are, how many frames they waste, and how sequence-number choices (modulo-2, "not told", modulo-1) can break them.

## What it does

- **Live Demo:** type any message. All three protocols send it over the same lossy channel, with a step-by-step trace.
- **Animation:** a time-space diagram of frames and ACKs between sender and receiver, with the sender and receiver windows, lost frames, timeouts and resent frames. It has Play, Step, Reset and a slider.
- **Sequence Numbering:** compares modulo-2 (0,1,0,1...), "not told" (0,1,2,3...) and modulo-1 (all 0), tests modulo 1 to 8, and runs 35 test cases per cell with different message sizes and lost frames.
- **Graphs:** four graphs from many random runs: throughput vs loss rate, throughput vs window size, frames sent per packet delivered, and simulation vs theory.

## Requirements

- Python 3.9 or newer
- Flask (for the web dashboard): `pip install flask`
- matplotlib (only for the stand-alone graph scripts): `pip install matplotlib`

## How to run

Web dashboard (recommended):

```
python app.py
```

Then open http://127.0.0.1:5000 in your browser. Press Ctrl+C in the terminal to stop it.

Terminal menu:

```
python main.py
```

Or run one part directly:

| Command | What it does |
| --- | --- |
| `python demo.py` | Asks for a message and runs all three protocols |
| `python numbering.py` | Numbering comparison in 4 parts |
| `python compare.py` | Throughput vs loss rate (saves a PNG) |
| `python window_test.py` | Throughput vs window size (saves a PNG) |
| `python theory.py` | Simulation vs theory (saves a PNG) |

## Project files

| File | Purpose |
| --- | --- |
| `channel.py` | Lossy channel (random loss or "every k-th lost") and sequence numbering |
| `stopwait.py` | Stop-and-Wait engine |
| `gbn.py` | Go-Back-N engine |
| `sr.py` | Selective Repeat engine |
| `demo.py` | Terminal demo |
| `numbering.py` | Sequence-numbering study |
| `compare.py`, `window_test.py`, `theory.py` | Stand-alone graph scripts |
| `main.py` | Terminal menu |
| `app.py` | Flask server for the dashboard |
| `templates/index.html` | Dashboard page (all four tabs) |

## How the simulation works

- Time moves in **ticks**. The sender sends at most one frame per tick. A frame or ACK takes `delay` ticks to cross the channel. A frame with no ACK after `timeout` ticks is resent.
- **Loss models:** random loss with a probability (used for the graphs and available in the demo), or a fixed rule: every k-th frame and/or every k-th ACK is lost (used for repeatable, explainable runs).
- **Sequence numbers:** frame i carries `i % modulo`, or just `i` when the modulo is "not told".
- **Go-Back-N** uses cumulative ACKs and one timer. The receiver discards out-of-order frames, and on timeout the sender goes back and resends from the oldest unacknowledged frame.
- **Selective Repeat** uses one ACK and one timer per frame. The receiver stores out-of-order frames, and only the lost frame is resent.
- A run that cannot finish (for example, a fixed loss rule hitting the same frame on every retry) is stopped by a safety limit and shown as "never finishes".

## Main findings

- With a large enough window, Selective Repeat is the fastest and Stop-and-Wait the slowest. Go-Back-N flattens as the window grows.
- Go-Back-N sends far more frames per delivered packet (about 4.5 at 30% loss, against about 2 for Selective Repeat and Stop-and-Wait).
- The Stop-and-Wait simulation matches its formula, T = 2d + ((1 - q) / q) * timeout with q = (1 - p)^2.
- Safe modulo: Stop-and-Wait needs 2, Go-Back-N needs window + 1, Selective Repeat needs 2 x window. Modulo-1 makes every frame look the same, so Go-Back-N never finishes and the others deliver wrong data once ACKs are lost.
- Example (message NETWORKS, window 3, every 4th frame lost, delay 2, timeout 6): Stop-and-Wait sends 10 frames in 45 ticks, Go-Back-N 19 frames in 48 ticks, Selective Repeat 10 frames in 25 ticks.

## Notes and limits

- The simulator is simplified: one fixed delay and timeout, one frame per tick, and each message letter is one frame (up to 20 letters in the demo).
- Graph results are averages of random runs, so they vary slightly between runs. Demo and numbering results with the "every k-th" rule are the same every time.