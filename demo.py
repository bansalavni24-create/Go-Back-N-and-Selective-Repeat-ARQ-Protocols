# Step-by-step demo: packets are dropped ON PURPOSE so you can watch recovery.
MESSAGE = "NETWORKS"       # each letter is one packet
WINDOW = 4
DELAY = 2                  # ticks for a packet to cross the channel
TIMEOUT = 6                # ticks to wait before assuming loss
DROP_THESE = {2, 5}        # packets lost the FIRST time they are sent


def go_back_n_demo():
    total = len(MESSAGE)
    dropped = set()
    base = next_seq = expected = 0
    timer_start = None
    data_road, ack_road, delivered = [], [], []
    time = 0
    print("=== GO-BACK-N DEMO ===")
    print(f"Message: {MESSAGE}   Window: {WINDOW}   Packets that will be lost: {sorted(DROP_THESE)}\n")

    while base < total:
        time += 1

        # 1. Sender collects ACKs
        for a in [a for a in ack_road if a[0] == time]:
            ack_road.remove(a)
            if a[1] > base:
                base = a[1]
                if next_seq < base:
                    next_seq = base
                timer_start = time if base < next_seq else None
                print(f"t={time:2d}  Sender   : ACK {a[1]} received -> window slides to [{base}..{base + WINDOW - 1}]")
            else:
                print(f"t={time:2d}  Sender   : ACK {a[1]} received (old ACK, nothing new)")

        # 2. Timeout -> go back
        if timer_start is not None and time - timer_start >= TIMEOUT:
            print(f"t={time:2d}  Sender   : TIMEOUT! Going back to packet {base} and resending from there")
            next_seq = base
            timer_start = None

        # 3. Send one packet
        if next_seq < base + WINDOW and next_seq < total:
            if base == next_seq:
                timer_start = time
            if next_seq in DROP_THESE and next_seq not in dropped:
                dropped.add(next_seq)
                print(f"t={time:2d}  Sender   : sends packet {next_seq} ({MESSAGE[next_seq]})  ---> LOST in channel")
            else:
                print(f"t={time:2d}  Sender   : sends packet {next_seq} ({MESSAGE[next_seq]})")
                data_road.append((time + DELAY, next_seq))
            next_seq += 1

        # 4. Receiver
        for d in [d for d in data_road if d[0] == time]:
            data_road.remove(d)
            seq = d[1]
            if seq == expected:
                delivered.append(MESSAGE[seq])
                expected += 1
                print(f"t={time:2d}  Receiver : got packet {seq} -> accepted. Message so far: {''.join(delivered)}")
            else:
                print(f"t={time:2d}  Receiver : got packet {seq} but wants {expected} -> DISCARDED")
            ack_road.append((time + DELAY, expected))
            print(f"t={time:2d}  Receiver : sends ACK {expected} (means: I want packet {expected} next)")

    sent_note = "".join(delivered)
    print(f"\nDONE at t={time}. Receiver got: {sent_note}  ->  {'CORRECT' if sent_note == MESSAGE else 'WRONG'}\n")


def selective_repeat_demo():
    total = len(MESSAGE)
    dropped = set()
    base = next_seq = rcv_base = 0
    acked, received, sent_at = set(), set(), {}
    data_road, ack_road, delivered = [], [], []
    time = 0
    print("=== SELECTIVE REPEAT DEMO ===")
    print(f"Message: {MESSAGE}   Window: {WINDOW}   Packets that will be lost: {sorted(DROP_THESE)}\n")

    def transmit(seq, note=""):
        sent_at[seq] = time
        if seq in DROP_THESE and seq not in dropped:
            dropped.add(seq)
            print(f"t={time:2d}  Sender   : sends packet {seq} ({MESSAGE[seq]}){note}  ---> LOST in channel")
        else:
            print(f"t={time:2d}  Sender   : sends packet {seq} ({MESSAGE[seq]}){note}")
            data_road.append((time + DELAY, seq))

    while base < total:
        time += 1

        # 1. Sender collects ACKs (one per packet)
        for a in [a for a in ack_road if a[0] == time]:
            ack_road.remove(a)
            acked.add(a[1])
            old = base
            while base in acked:
                base += 1
            if base != old:
                print(f"t={time:2d}  Sender   : ACK {a[1]} received -> window slides to [{base}..{base + WINDOW - 1}]")
            else:
                print(f"t={time:2d}  Sender   : ACK {a[1]} received (window cannot slide yet, packet {base} still missing)")

        # 2. Send one packet: resend a timed-out one, else a new one
        resend = None
        for seq in range(base, next_seq):
            if seq not in acked and time - sent_at[seq] >= TIMEOUT:
                resend = seq
                break
        if resend is not None:
            print(f"t={time:2d}  Sender   : TIMEOUT for packet {resend}! Resending ONLY packet {resend}")
            transmit(resend)
        elif next_seq < base + WINDOW and next_seq < total:
            transmit(next_seq)
            next_seq += 1

        # 3. Receiver
        for d in [d for d in data_road if d[0] == time]:
            data_road.remove(d)
            seq = d[1]
            if seq >= rcv_base:
                received.add(seq)
            while rcv_base in received:
                delivered.append(MESSAGE[rcv_base])
                rcv_base += 1
            if seq >= rcv_base:
                print(f"t={time:2d}  Receiver : got packet {seq} out of order -> STORED. Message so far: {''.join(delivered)}")
            else:
                print(f"t={time:2d}  Receiver : got packet {seq} -> accepted. Message so far: {''.join(delivered)}")
            ack_road.append((time + DELAY, seq))
            print(f"t={time:2d}  Receiver : sends ACK {seq} (means: I got packet {seq})")

    result = "".join(delivered)
    print(f"\nDONE at t={time}. Receiver got: {result}  ->  {'CORRECT' if result == MESSAGE else 'WRONG'}\n")


if __name__ == "__main__":
    go_back_n_demo()
    input("Press Enter to see Selective Repeat on the same losses...")
    print()
    selective_repeat_demo()