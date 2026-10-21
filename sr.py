from channel import Channel, seq_number


def run_selective_repeat(message, window_size, loss_prob=0.0, delay=5, timeout=12,
                         every_kth=0, ack_every_kth=0, modulo=None,
                         log=False, max_ticks=None):
    """Send a message with Selective Repeat. Settings are the same as Go-Back-N."""
    data = list(message) if isinstance(message, str) else list(range(message))
    total = len(data)
    if max_ticks is None:
        max_ticks = 100 * (total + 10) + 2000
    data_channel = Channel(loss_prob if every_kth == 0 else 0.0, every_kth)
    ack_channel = Channel(loss_prob if (every_kth == 0 and ack_every_kth == 0) else 0.0, ack_every_kth)

    base = 0             # oldest frame not yet acknowledged
    next_seq = 0         # next NEW frame to send
    acked = set()        # sender: frames already acknowledged
    sent_at = {}         # sender: when each frame was last sent
    rcv_base = 0         # receiver: next frame needed in order
    received = {}        # receiver: frames stored (even out of order)
    delivered = []
    data_road, ack_road = [], []
    time = sent = 0

    def say(who, text):
        if log:
            print(f"t={time:3d}  {who:<9s}: {text}")

    def transmit(frame):
        nonlocal sent
        sent += 1
        sent_at[frame] = time
        seq = seq_number(frame, modulo)
        lost = data_channel.lost()
        say("Sender", f"sends frame {frame} '{data[frame]}' (seq {seq}) window [{base}..{base + window_size - 1}]"
                      f"{'  ---> LOST in channel' if lost else ''}")
        if not lost:
            data_road.append((time + delay, frame, seq))

    while base < total and time < max_ticks:
        time += 1

        # 1. Sender: ACKs that arrive now (each ACK is for ONE frame)
        for arrival, ack in [a for a in ack_road if a[0] <= time]:
            which = None
            for f in range(base, next_seq):
                if f not in acked and seq_number(f, modulo) == ack:
                    which = f
                    break
            if which is None:
                say("Sender", f"ACK {ack} received (nothing new)")
            else:
                acked.add(which)
                old = base
                while base in acked:
                    base += 1                              # window slides forward
                if base != old:
                    say("Sender", f"ACK {ack} received -> window slides to [{base}..{base + window_size - 1}]")
                else:
                    say("Sender", f"ACK {ack} received (window cannot slide yet, frame {base} still missing)")
        ack_road = [a for a in ack_road if a[0] > time]

        # 2. Sender: send ONE frame this tick. First choice: resend a timed-out frame
        resend = None
        for f in range(base, next_seq):
            if f not in acked and time - sent_at[f] >= timeout:
                resend = f
                break
        if resend is not None:
            say("Sender", f"TIMEOUT for frame {resend}! Resending ONLY frame {resend}")
            transmit(resend)
        elif next_seq < base + window_size and next_seq < total:
            transmit(next_seq)
            next_seq += 1

        # 3. Receiver: frames that arrive now
        for arrival, fid, seq in [d for d in data_road if d[0] <= time]:
            slot = None
            for f in range(rcv_base, rcv_base + window_size):
                if seq_number(f, modulo) == seq:
                    slot = f
                    break
            if slot is None or slot in received:
                say("Receiver", f"got frame {fid} (seq {seq}) again -> already have it, just ACK it")
            else:
                received[slot] = data[fid]
                while rcv_base in received:
                    delivered.append(received.pop(rcv_base))
                    rcv_base += 1
                if slot < rcv_base:
                    say("Receiver", f"got frame {fid} (seq {seq}) -> accepted. Message so far: {''.join(map(str, delivered))}")
                else:
                    say("Receiver", f"got frame {fid} (seq {seq}) out of order -> STORED. Message so far: {''.join(map(str, delivered))}")
            lost = ack_channel.lost()
            say("Receiver", f"sends ACK {seq} (I got frame with seq {seq}){'  ---> LOST in channel' if lost else ''}")
            if not lost:
                ack_road.append((time + delay, seq))
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
def selective_repeat(total_packets, window_size, loss_prob, delay=5, timeout=12):
    r = run_selective_repeat(total_packets, window_size, loss_prob, delay, timeout)
    return r["time"], r["sent"]


# This test runs only when you run sr.py directly
if __name__ == "__main__":
    total = 100
    time, sent = selective_repeat(total, window_size=8, loss_prob=0.0)
    print("Loss 0%  -> time:", time, "ticks, packets resent:", sent - total)
    time, sent = selective_repeat(total, window_size=8, loss_prob=0.1)
    print("Loss 10% -> time:", time, "ticks, packets resent:", sent - total)
    print()
    run_selective_repeat("HELLO", window_size=3, delay=2, timeout=6, every_kth=4, modulo=6, log=True)