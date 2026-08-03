# run.py
import os
import sys
import subprocess

def main():
    print("==================================================")
    print("          LOOM PROTOCOL (ATP) DEMO CLI            ")
    print("==================================================")
    print("1) Run Concurrent Collision Stress Test (Agents)")
    print("2) Run End-to-End Simple Buyer Bot Example")
    print("3) Start Local ATP API Gateway")
    print("4) Exit")
    print("==================================================")
    
    choice = input("Select an option to execute (1-4): ").strip()
    print("\n")

    # Get the absolute path to the root directory
    root_dir = os.path.dirname(os.path.abspath(__file__))

    if choice == "1":
        print("[System] Launching Multi-Threaded Collision Engine...\n")
        script_path = os.path.join(root_dir, "tests", "stress", "collision_test.py")
        subprocess.run([sys.executable, script_path])
    elif choice == "2":
        print("[System] Launching 3rd-Party SDK Integration Example...\n")
        script_path = os.path.join(root_dir, "examples", "bots", "simple_buyer.py")
        subprocess.run([sys.executable, script_path])
    elif choice == "3":
        print("[System] Starting Local ATP API Gateway...\n")
        subprocess.run([sys.executable, "-m", "core.api.server"])
    elif choice == "4":
        print("Exiting Loom Protocol Controller. Happy Hacking!")
        sys.exit(0)
    else:
        print("[Error] Invalid choice. Please run the script again.")

if __name__ == "__main__":
    main()
