import subprocess
import sys

MENU = [
    ("1", "Demo: type a message, see all 3 protocols step by step", "demo.py"),
    ("2", "Numbering: modulo-2, not told, modulo-1, message sizes", "numbering.py"),
    ("3", "Graph: speed vs loss rate", "compare.py"),
    ("4", "Graph: speed vs window size", "window_test.py"),
    ("5", "Graph: simulation vs theory", "theory.py"),
]


def run_file(filename):
    print(f"\n--- Running {filename} ---\n")
    subprocess.run([sys.executable, filename])
    print(f"\n--- Finished {filename} ---")


def main():
    while True:
        print("\n" + "=" * 60)
        print("  GO-BACK-N and SELECTIVE REPEAT: PERFORMANCE ANALYSIS")
        print("=" * 60)
        for key, text, _ in MENU:
            print(f"  {key}. {text}")
        print("  0. Exit")
        choice = input("\nPick a number: ").strip()
        if choice == "0":
            print("Bye!")
            break
        for key, _, filename in MENU:
            if choice == key:
                run_file(filename)
                break
        else:
            print("Please type a number from the menu.")


if __name__ == "__main__":
    main()