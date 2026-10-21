import random

# Old function (kept so your older files still work)
def send_through_channel(packet, loss_probability):
    if random.random() < loss_probability:
        return None      # packet lost
    return packet        # packet delivered


class Channel:
    """A channel that can lose things in two ways:
         random loss     -> Channel(loss_prob=0.2)  about 2 in 10 are lost
         fixed-rule loss -> Channel(every_kth=4)    every 4th thing is lost
    """
    def __init__(self, loss_prob=0.0, every_kth=0):
        self.loss_prob = loss_prob
        self.every_kth = every_kth
        self.count = 0                      # how many things have passed through

    def lost(self):
        self.count += 1
        if self.every_kth > 0:
            return self.count % self.every_kth == 0
        return random.random() < self.loss_prob


def seq_number(frame, modulo):
    """The sequence number written on a frame.
       modulo=None -> keep counting 0, 1, 2, 3 ...
       modulo=2    -> 0, 1, 0, 1 ...
       modulo=1    -> 0, 0, 0, 0 ...
    """
    if modulo is None:
        return frame
    return frame % modulo


# This test runs only when you run channel.py directly
if __name__ == "__main__":
    ch = Channel(every_kth=4)
    print("Every 4th lost, first 8 things:", [ch.lost() for _ in range(8)])
    ch = Channel(loss_prob=0.2)
    lost = sum(ch.lost() for _ in range(1000))
    print("Random 20% loss, lost out of 1000:", lost)
    print("Modulo-2 numbers:", [seq_number(i, 2) for i in range(6)])
    print("Modulo-1 numbers:", [seq_number(i, 1) for i in range(6)])
    print("No modulo numbers:", [seq_number(i, None) for i in range(6)])