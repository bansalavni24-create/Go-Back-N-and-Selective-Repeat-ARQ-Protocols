import matplotlib.pyplot as plt
from gbn import go_back_n
from sr import selective_repeat

TOTAL = 100        # packets in the file
LOSS = 0.10        # fixed loss rate (10%)
RUNS = 100         # repeat each setting this many times
window_sizes = [1, 2, 4, 8, 12, 16, 24, 32]

def average_throughput(protocol, window):
    values = []
    for _ in range(RUNS):
        time, sent = protocol(TOTAL, window, LOSS)
        values.append(TOTAL / time)
    return sum(values) / len(values)

gbn_results = []
sr_results = []
print("Window    GBN throughput    SR throughput")
for w in window_sizes:
    g = average_throughput(go_back_n, w)
    s = average_throughput(selective_repeat, w)
    gbn_results.append(g)
    sr_results.append(s)
    print(f"{w:6d}   {g:14.3f}   {s:13.3f}")

plt.plot(window_sizes, gbn_results, marker="o", label="Go-Back-N")
plt.plot(window_sizes, sr_results, marker="s", label="Selective Repeat")
plt.xlabel("Window size (packets)")
plt.ylabel("Throughput (packets per tick)")
plt.title("Throughput vs Window Size (loss = 10%)")
plt.legend()
plt.grid(True)
plt.savefig("throughput_vs_window.png", dpi=150)
plt.show()