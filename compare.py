import matplotlib.pyplot as plt
from gbn import go_back_n
from sr import selective_repeat

TOTAL = 100        # packets in the file
WINDOW = 8         # window size
RUNS = 100         # repeat each setting this many times
loss_rates = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]

def average_throughput(protocol, loss):
    values = []
    for _ in range(RUNS):
        time, sent = protocol(TOTAL, WINDOW, loss)
        values.append(TOTAL / time)          # useful packets per tick
    return sum(values) / len(values)

gbn_results = []
sr_results = []
print("Loss    GBN throughput    SR throughput")
for loss in loss_rates:
    g = average_throughput(go_back_n, loss)
    s = average_throughput(selective_repeat, loss)
    gbn_results.append(g)
    sr_results.append(s)
    print(f"{loss*100:4.0f}%   {g:14.3f}   {s:13.3f}")

percent = [l * 100 for l in loss_rates]
plt.plot(percent, gbn_results, marker="o", label="Go-Back-N")
plt.plot(percent, sr_results, marker="s", label="Selective Repeat")
plt.xlabel("Packet loss rate (%)")
plt.ylabel("Throughput (packets per tick)")
plt.title("Throughput vs Loss Rate (window = 8)")
plt.legend()
plt.grid(True)
plt.savefig("throughput_vs_loss.png", dpi=150)
plt.show()