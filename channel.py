import random

def send_through_channel(packet, loss_probability):
    if random.random() < loss_probability:
        return None      # packet lost
    return packet        # packet delivered

# This test runs only when you run channel.py directly
if __name__ == "__main__":
    lost = 0
    for i in range(1000):
        if send_through_channel(i, 0.2) is None:
            lost += 1
    print("Packets sent: 1000")
    print("Packets lost:", lost)