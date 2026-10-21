from channel import Channel, seq_number


def run_stop_and_wait(message, loss_prob=0.0, delay=5, timeout=12,
                      every_kth=0, ack_every_kth=0, modulo=None,
                      log=False, max_ticks=None):
    """Send a message with Stop-and-Wait: one frame at a time, wait for its ACK.
       message   : a text like "HELLO" (one letter = one frame) or a number of frames
       every_kth : lose every k-th frame (ACKs are then not lost unless ack_every_kth is set)
       modulo    : None (keep counting), 2 (0,1,0,1...), 1 (all zero) ...
       log       : True = print every step
    """
    data = list(message) if isinstance(message, str) else list(range(message))
    total = len(data)
    if max_ticks is None:
        max_ticks = 100 * (total + 10) + 2000
    data_channel = Channel(loss_prob if every_kth == 0 else 0.0, every_kth)
    ack_channel = Channel(loss_prob if (every_kth == 0 and ack_every_kth == 0) else 0.0, ack_every_kth)

    frame = 0            # the frame the sender is working on
    sent_time = None     # when it was last sent (None = not waiting for an ACK)
    rcv_next = 0         # receiver: the frame it wants next
    delivered = []
    data_road, ack_road = [], []
    time = sent = 0

    def say(who, text):
        if log:
            print(f"t={time:3d}  {who:<9s}: {text}")

    while frame < total and time < max_ticks:
        time += 1

        # 1. Sender: ACKs that arrive now
        for arrival, ack in [a for a in ack_road if a[0] <= time]:
            if frame < total and ack == seq_number(frame + 1, modulo):
                say("Sender", f"ACK {ack} received -> frame {frame} is done, move to the next")
                frame += 1
                sent_time = None
            else:
                say("Sender", f"ACK {ack} received (not what I was waiting for, ignored)")
        ack_road = [a for a in ack_road if a[0] > time]

        # 2. Sender: timeout?
        if sent_time is not None and time - sent_time >= timeout:
            say("Sender", f"TIMEOUT! No ACK for frame {frame}, so resend it")
            sent_time = None

        # 3. Sender: send the current frame if not waiting
        if sent_time is None and frame < total:
            sent += 1
            sent_time = time
            seq = seq_number(frame, modulo)
            lost = data_channel.lost()
            say("Sender", f"sends frame {frame} '{data[frame]}' (seq {seq}){'  ---> LOST in channel' if lost else ''}")
            if not lost:
                data_road.append((time + delay, frame, seq))

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

    finished = frame >= total
    correct = delivered == data
    text = "".join(map(str, delivered)) if isinstance(message, str) else delivered
    if log:
        if finished:
            print(f"\nDONE at t={time}. Frames sent: {sent}. Receiver got: {text} -> {'CORRECT' if correct else 'WRONG'}")
        else:
            print(f"\nGAVE UP at t={time}. Frames sent: {sent}. This never finishes with these settings.")
    return {"time": time, "sent": sent, "delivered": text, "correct": correct, "finished": finished}


# This test runs only when you run stopwait.py directly
if __name__ == "__main__":
    run_stop_and_wait("HELLO", delay=2, timeout=6, every_kth=4, modulo=2, log=True)