from channel import Channel, seq_number


def run_go_back_n(message, window_size, loss_prob=0.0, delay=5, timeout=12,
                  every_kth=0, ack_every_kth=0, modulo=None,
                  log=False, max_ticks=None):
    """Send a message with Go-Back-N. Settings are the same as Stop-and-Wait,
       plus window_size (how many frames can be on the road at once)."""
    data = list(message) if isinstance(message, str) else list(range(message))
    total = len(data)
    if max_ticks is None:
        max_ticks = 100 * (total + 10) + 2000
    data_channel = Channel(loss_prob if every_kth == 0 else 0.0, every_kth)
    ack_channel = Channel(loss_prob if (every_kth == 0 and ack_every_kth == 0) else 0.0, ack_every_kth)

    base = 0             # oldest frame not yet acknowledged
    next_seq = 0         # next frame to send
    high = 0             # highest frame sent so far + 1
    rcv_next = 0         # receiver: the frame it wants next
    timer = None         # when the timer started (None = no timer)
    delivered = []
    data_road, ack_road = [], []
    time = sent = 0

    def say(who, text):
        if log:
            print(f"t={time:3d}  {who:<9s}: {text}")

    while base < total and time < max_ticks:
        time += 1

        # 1. Sender: ACKs that arrive now
        for arrival, ack in [a for a in ack_road if a[0] <= time]:
            n = (ack - base) if modulo is None else (ack - base) % modulo
            if 1 <= n <= high - base:
                base += n                                  # window slides forward
                next_seq = max(next_seq, base)
                timer = time if base < next_seq else None
                say("Sender", f"ACK {ack} received -> window slides to [{base}..{base + window_size - 1}]")
            else:
                say("Sender", f"ACK {ack} received (nothing new)")
        ack_road = [a for a in ack_road if a[0] > time]

        # 2. Sender: timeout? Go back to the oldest unacknowledged frame
        if timer is not None and time - timer >= timeout:
            say("Sender", f"TIMEOUT! Going back to frame {base} and resending from there")
            next_seq, timer = base, None

        # 3. Sender: send one frame if the window has room
        if next_seq < base + window_size and next_seq < total:
            sent += 1
            if base == next_seq:
                timer = time
            seq = seq_number(next_seq, modulo)
            lost = data_channel.lost()
            say("Sender", f"sends frame {next_seq} '{data[next_seq]}' (seq {seq}) window [{base}..{base + window_size - 1}]"
                          f"{'  ---> LOST in channel' if lost else ''}")
            if not lost:
                data_road.append((time + delay, next_seq, seq))
            next_seq += 1
            high = max(high, next_seq)

        # 4. Receiver: frames that arrive now
        for arrival, fid, seq in [d for d in data_road if d[0] <= time]:
            if seq == seq_number(rcv_next, modulo):
                delivered.append(data[fid])
                rcv_next += 1
                say("Receiver", f"got frame {fid} (seq {seq}) -> accepted. Message so far: {''.join(map(str, delivered))}")
            else:
                say("Receiver", f"got frame {fid} (seq {seq}) but expects seq {seq_number(rcv_next, modulo)} -> DISCARDED")
            ack = seq_number(rcv_next, modulo)
            lost = ack_channel.lost()
            say("Receiver", f"sends ACK {ack} (next frame expected){'  ---> LOST in channel' if lost else ''}")
            if not lost:
                ack_road.append((time + delay, ack))
        data_road = [d for d in data_road if d[0] > time]

    finished = base >= total
    correct = delivered == data
    text = "".join(map(str, delivered)) if isinstance(message, str) else delivered
    if log:
        if finished:
            print(f"\nDONE at t={time}. Frames sent: {sent}. Receiver got: {text} -> {'CORRECT' if correct else 'WRONG'}")
        else:
            print(f"\nGAVE UP at t={time}. Frames sent: {sent}. This never finishes with these settings.")
    return {"time": time, "sent": sent, "delivered": text, "correct": correct, "finished": finished}


# The old way of calling it still works (compare.py, window_test.py, theory.py use this)
def go_back_n(total_packets, window_size, loss_prob, delay=5, timeout=12):
    r = run_go_back_n(total_packets, window_size, loss_prob, delay, timeout)
    return r["time"], r["sent"]


# This test runs only when you run gbn.py directly
if __name__ == "__main__":
    total = 100
    time, sent = go_back_n(total, window_size=8, loss_prob=0.0)
    print("Loss 0%  -> time:", time, "ticks, packets resent:", sent - total)
    time, sent = go_back_n(total, window_size=8, loss_prob=0.1)
    print("Loss 10% -> time:", time, "ticks, packets resent:", sent - total)
    print()
    run_go_back_n("HELLO", window_size=3, delay=2, timeout=6, every_kth=4, modulo=4, log=True, max_ticks=60)