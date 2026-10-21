from stopwait import run_stop_and_wait
from gbn import run_go_back_n
from sr import run_selective_repeat

# ---- Settings you can change ----
WINDOW = 3            # window size for Go-Back-N and Selective Repeat
EVERY_KTH = 4         # every 4th frame sent is lost
ACK_EVERY_KTH = 3     # in the "ACKs also lost" tests, every 3rd ACK is lost
DELAY = 2
TIMEOUT = 6

PROTOCOLS = ["Stop-and-Wait", "Go-Back-N", "Selective Repeat"]
SCHEMES = [("Modulo-2   (0,1,0,1...)", 2),
           ("Not told   (0,1,2,3...)", None),
           ("Modulo-1   (0,0,0,0...)", 1)]


def nth(n):
    """1 -> 1st, 2 -> 2nd, 3 -> 3rd, 4 -> 4th ..."""
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}" + {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def run(protocol, message, modulo, every_kth, ack_every_kth):
    settings = dict(delay=DELAY, timeout=TIMEOUT, every_kth=every_kth,
                    ack_every_kth=ack_every_kth, modulo=modulo,
                    max_ticks=300 + 30 * len(message))
    if protocol == "Stop-and-Wait":
        return run_stop_and_wait(message, **settings)
    if protocol == "Go-Back-N":
        return run_go_back_n(message, WINDOW, **settings)
    return run_selective_repeat(message, WINDOW, **settings)


def status(r):
    if not r["finished"]:
        return "never finishes"
    return "correct" if r["correct"] else "WRONG"


def part_table(message, ack_every_kth):
    print(f"{'Numbering':<26}" + "".join(f"{p:<22}" for p in PROTOCOLS))
    problems = []
    for name, modulo in SCHEMES:
        line = f"{name:<26}"
        for p in PROTOCOLS:
            r = run(p, message, modulo, EVERY_KTH, ack_every_kth)
            cell = status(r) if not r["finished"] else f"{r['sent']} frames, {status(r)}"
            line += f"{cell:<22}"
            if status(r) != "correct":
                got = r["delivered"] if r["finished"] else r["delivered"][:12] + "..."
                problems.append(f"  {p} with {name.split('(')[0].strip()}: receiver got '{got}'")
        print(line)
    if problems:
        print("\nWhat the receiver got when it went wrong:")
        for p in problems:
            print(p)


def modulo_table(message):
    print(f"{'Modulo':<20}" + "".join(f"{m:<8}" for m in range(1, 9)))
    for p in PROTOCOLS:
        line = f"{p:<20}"
        for m in range(1, 9):
            r = run(p, message, m, EVERY_KTH, ACK_EVERY_KTH)
            word = "stuck" if not r["finished"] else ("ok" if r["correct"] else "bad")
            line += f"{word:<8}"
        print(line)
    print(f"\nSafe rule: Stop-and-Wait needs 2.  Go-Back-N needs window + 1 = {WINDOW + 1}.  "
          f"Selective Repeat needs 2 x window = {2 * WINDOW}.")
    print("A smaller number can work by luck on one message, so rely on the rule.")


def sweep_table(ack_every_kth):
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    sizes = [4, 6, 8, 10, 12, 16, 20]
    losses = [3, 4, 5, 6, 8]
    total = len(sizes) * len(losses)
    print(f"{'Numbering':<26}" + "".join(f"{p:<34}" for p in PROTOCOLS))
    for name, modulo in SCHEMES:
        line = f"{name:<26}"
        for p in PROTOCOLS:
            good = stuck = 0
            for n in sizes:
                for k in losses:
                    r = run(p, letters[:n], modulo, k, ack_every_kth)
                    if not r["finished"]:
                        stuck += 1
                    elif r["correct"]:
                        good += 1
            cell = f"{good} of {total} correct"
            if stuck:
                cell += f", {stuck} stuck"
            line += f"{cell:<34}"
        print(line)


def main():
    message = input("Type the message you want to send: ").strip()
    if message == "":
        message = "NETWORKS"
        print("No message typed, using NETWORKS")
    message = message[:20]
    print(f"\nMessage: {message}   Window: {WINDOW}   Every {nth(EVERY_KTH)} frame sent is lost")

    print("\n" + "=" * 78)
    print("PART 1: Only frames are lost (like the exam, no ACK is lost)")
    print("=" * 78)
    part_table(message, 0)
    input("\nPress Enter for Part 2...")

    print("\n" + "=" * 78)
    print(f"PART 2: Frames AND ACKs are lost (every {nth(ACK_EVERY_KTH)} ACK is lost too)")
    print("=" * 78)
    part_table(message, ACK_EVERY_KTH)
    input("\nPress Enter for Part 3...")

    print("\n" + "=" * 78)
    print("PART 3: Which modulo is enough? (frames and ACKs lost, ok = message correct)")
    print("=" * 78)
    modulo_table(message)
    input("\nPress Enter for Part 4...")

    print("\n" + "=" * 78)
    print("PART 4: Different message sizes and different lost frames")
    print("=" * 78)
    print("35 tests per cell: message sizes 4,6,8,10,12,16,20 and every 3rd,4th,5th,6th,8th frame lost")
    print("\nOnly frames lost:")
    sweep_table(0)
    print(f"\nFrames and ACKs lost (every {nth(ACK_EVERY_KTH)} ACK):")
    sweep_table(ACK_EVERY_KTH)


if __name__ == "__main__":
    main()