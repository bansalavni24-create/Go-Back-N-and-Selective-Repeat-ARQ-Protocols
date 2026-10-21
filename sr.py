from channel import send_through_channel

def selective_repeat(total_packets, window_size, loss_prob, delay=5, timeout=12):
    base = 0              # oldest packet not yet acknowledged
    next_seq = 0          # next NEW packet number to send
    acked = set()         # sender: packets already acknowledged
    sent_at = {}          # sender: when each packet was last sent
    rcv_base = 0          # receiver: next packet needed in order
    received = set()      # receiver: packets stored (even out of order)
    data_on_road = []     # (arrival_time, number)
    acks_on_road = []     # (arrival_time, number)
    time = 0
    packets_sent = 0

    def transmit(seq):
        nonlocal packets_sent
        packets_sent += 1
        sent_at[seq] = time
        if send_through_channel(seq, loss_prob) is not None:
            data_on_road.append((time + delay, seq))

    while base < total_packets:
        time += 1

        # 1. Sender: collect ACKs (each ACK is for ONE packet)
        arrived = [a for a in acks_on_road if a[0] <= time]
        acks_on_road = [a for a in acks_on_road if a[0] > time]
        for arrival_time, ack_number in arrived:
            acked.add(ack_number)
        while base in acked:
            base += 1                                  # window slides forward

        # 2. Sender: send ONE packet this tick
        #    first choice: resend the oldest packet whose timer ran out
        resend = None
        for seq in range(base, next_seq):
            if seq not in acked and time - sent_at[seq] >= timeout:
                resend = seq
                break
        if resend is not None:
            transmit(resend)                           # only the lost packet
        elif next_seq < base + window_size and next_seq < total_packets:
            transmit(next_seq)                         # otherwise a new packet
            next_seq += 1

        # 3. Receiver: collect packets, store them, ACK each one
        arrived = [d for d in data_on_road if d[0] <= time]
        data_on_road = [d for d in data_on_road if d[0] > time]
        for arrival_time, seq in arrived:
            if rcv_base - window_size <= seq < rcv_base + window_size:
                if seq >= rcv_base:
                    received.add(seq)                  # keep out-of-order packets
                if send_through_channel(seq, loss_prob) is not None:
                    acks_on_road.append((time + delay, seq))
        while rcv_base in received:
            rcv_base += 1                              # deliver in order

    return time, packets_sent


# Test
if __name__ == "__main__":
    total = 100
    time, sent = selective_repeat(total, window_size=8, loss_prob=0.0)
    print("Loss 0%  -> time:", time, "ticks, packets resent:", sent - total)
    time, sent = selective_repeat(total, window_size=8, loss_prob=0.1)
    print("Loss 10% -> time:", time, "ticks, packets resent:", sent - total)