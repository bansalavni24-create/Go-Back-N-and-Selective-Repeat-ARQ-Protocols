import matplotlib.pyplot as plt
from gbn import go_back_n
from sr import selective_repeat

TOTAL = 500        # packets in the file
WINDOW = 32        # window size for GBN and SR
RUNS = 30          # repeat each setting this many times
DELAY = 5          # same delay used inside gbn.py and sr.py
TIMEOUT = 12       # same timeout used inside gbn.py and sr.py
loss_rates = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]

def average_throughput(protocol, window, loss):
    values = []
    for _ in range(RUNS):
        time, sent = protocol(TOTAL, window, loss)
        values.append(TOTAL / time)
    return sum(values) / len(values)

# Theory 1: Stop-and-Wait. A packet needs BOTH the data and its ACK to survive.
def theory_stop_and_wait(p):
    q = (1 - p) ** 2                                  # chance one try succeeds
    time_per_packet = 2 * DELAY + (1 - q) / q * TIMEOUT
    return 1 / time_per_packet

# Theory 2: ideal Selective Repeat with a big window = chance one try succeeds
def theory_selective_repeat(p):
    return (1 - p) ** 2

sw, gbn, sr, th_sw, th_sr = [], [], [], [], []
print("Loss   StopWait  (theory)    GBN     SR   (theory)")
for p in loss_rates:
    a = average_throughput(go_back_n, 1, p)           # window 1 = Stop-and-Wait
    b = average_throughput(go_back_n, WINDOW, p)
    c = average_throughput(selective_repeat, WINDOW, p)
    sw.append(a); gbn.append(b); sr.append(c)
    th_sw.append(theory_stop_and_wait(p))
    th_sr.append(theory_selective_repeat(p))
    print(f"{p*100:3.0f}%   {a:7.3f}  {th_sw[-1]:7.3f}   {b:6.3f} {c:6.3f}  {th_sr[-1]:7.3f}")

x = [p * 100 for p in loss_rates]
plt.plot(x, sr, marker="s", color="tab:orange", label="Selective Repeat (simulated)")
plt.plot(x, th_sr, linestyle="--", color="tab:orange", label="Selective Repeat (theory)")
plt.plot(x, gbn, marker="o", color="tab:blue", label="Go-Back-N (simulated)")
plt.plot(x, sw, marker="^", color="tab:green", label="Stop-and-Wait (simulated)")
plt.plot(x, th_sw, linestyle="--", color="tab:green", label="Stop-and-Wait (theory)")
plt.xlabel("Packet loss rate (%)")
plt.ylabel("Throughput (packets per tick)")
plt.title(f"Simulation vs Theory (window = {WINDOW})")
plt.legend()
plt.grid(True)
plt.savefig("simulation_vs_theory.png", dpi=150)
plt.show()