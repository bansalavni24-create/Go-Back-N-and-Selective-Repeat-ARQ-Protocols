from channel import send_through_channel

def go_back_n(total_packets, window_size, loss_prob, delay=5, timeout=12):
    base = 0            # oldest packet not yet acknowledged
    next_seq = 0        # next packet number to send
    expected = 0        # receiver: packet number it wants next
    timer_start = None  # when the timer started (None = no timer)
    data_on_road = []   # packets travelling to receiver: (arrival_time, number)
    acks_on_road = []   # ACKs travelling back: (arrival_time, ack_number)
    time = 0
    packets_sent = 0

    while base < total_packets:
        time += 1

        # 1. Sender: collect ACKs that arrive now
        arrived = [a for a in acks_on_road if a[0] <= time]
        acks_on_road = [a for a in acks_on_road if a[0] > time]
        for arrival_time, ack_number in arrived:
            if ack_number > base:
                base = ack_number                      # window slides forward
                if next_seq < base:
                    next_seq = base
                timer_start = time if base < next_seq else None

        # 2. Sender: timeout? Go back to the oldest unacknowledged packet
        if timer_start is not None and time - timer_start >= timeout:
            next_seq = base
            timer_start = None

        # 3. Sender: send one packet if the window has room
        if next_seq < base + window_size and next_seq < total_packets:
            packets_sent += 1
            if base == next_seq:
                timer_start = time
            if send_through_channel(next_seq, loss_prob) is not None:
                data_on_road.append((time + delay, next_seq))
            next_seq += 1

        # 4. Receiver: collect packets that arrive now
        arrived = [d for d in data_on_road if d[0] <= time]
        data_on_road = [d for d in data_on_road if d[0] > time]
        for arrival_time, seq in arrived:
            if seq == expected:
                expected += 1                          # accept only in order
            if send_through_channel(expected, loss_prob) is not None:
                acks_on_road.append((time + delay, expected))

    return time, packets_sent


# Test
if __name__ == "__main__":
    total = 100
    time, sent = go_back_n(total, window_size=8, loss_prob=0.0)
    print("Loss 0%  -> time:", time, "ticks, packets resent:", sent - total)
    time, sent = go_back_n(total, window_size=8, loss_prob=0.1)
    print("Loss 10% -> time:", time, "ticks, packets resent:", sent - total)