from stopwait import run_stop_and_wait
from gbn import run_go_back_n
from sr import run_selective_repeat

# ---- Settings that can change ----
WINDOW = 3          # window size for Go-Back-N and Selective Repeat
EVERY_KTH = 5       # every Kth frame the sender transmits is lost
DELAY = 2           # ticks for a frame to cross the channel
TIMEOUT = 6         # ticks to wait for an ACK before resending
MAX_LETTERS = 20    # longest message allowed (keeps the printout readable)

# Smallest sequence-number range that works for each protocol
MODULO_SW = 2                 # Stop-and-Wait: 0, 1, 0, 1 ...
MODULO_GBN = WINDOW + 1       # Go-Back-N: window + 1
MODULO_SR = 2 * WINDOW        # Selective Repeat: 2 x window


def main():
    message = input("Type the message you want to send: ").strip()
    if message == "":
        message = "NETWORKS"
        print("No message typed, using NETWORKS")
    if len(message) > MAX_LETTERS:
        message = message[:MAX_LETTERS]
        print(f"Too long, using the first {MAX_LETTERS} letters: {message}")

    print(f"\nMessage: {message}   ({len(message)} letters = {len(message)} frames)")
    print(f"Every {EVERY_KTH}th frame sent is lost. No ACK is lost.")
    print(f"Window: {WINDOW}   Delay: {DELAY} ticks   Timeout: {TIMEOUT} ticks\n")

    common = dict(delay=DELAY, timeout=TIMEOUT, every_kth=EVERY_KTH, log=True,
                  max_ticks=300 + 30 * len(message))
    results = []

    print("=" * 70)
    print(f"STOP-AND-WAIT  (one frame at a time, sequence numbers modulo-{MODULO_SW}: 0,1,0,1...)")
    print("=" * 70)
    results.append(("Stop-and-Wait", run_stop_and_wait(message, modulo=MODULO_SW, **common)))
    input("\nPress Enter to see Go-Back-N on the same lost frames...")

    print("\n" + "=" * 70)
    print(f"GO-BACK-N  (window {WINDOW}, sequence numbers modulo-{MODULO_GBN})")
    print("=" * 70)
    results.append(("Go-Back-N", run_go_back_n(message, WINDOW, modulo=MODULO_GBN, **common)))
    input("\nPress Enter to see Selective Repeat on the same lost frames...")

    print("\n" + "=" * 70)
    print(f"SELECTIVE REPEAT  (window {WINDOW}, sequence numbers modulo-{MODULO_SR})")
    print("=" * 70)
    results.append(("Selective Repeat", run_selective_repeat(message, WINDOW, modulo=MODULO_SR, **common)))

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"{'Protocol':<18}{'Frames sent':>12}{'Time (ticks)':>14}   Result")
    for name, r in results:
        if not r["finished"]:
            result = "never finished"
        elif r["correct"]:
            result = "message correct"
        else:
            result = "message WRONG"
        print(f"{name:<18}{r['sent']:>12}{r['time']:>14}   {result}")
    print(f"\nFrames needed without any loss: {len(message)}")


if __name__ == "__main__":
    main()