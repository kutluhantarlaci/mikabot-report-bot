import subprocess
import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))

print("Which mode do you want to run?")
print("  1 - discovery  (run all commands once, build knowledge base)")
print("  2 - monitor    (continuous market monitoring + coin suggestions)")
print("  3 - main       (quick one-off test)")

choice = input("\nEnter 1, 2 or 3: ").strip()

scripts = {'1': 'discovery.py', '2': 'monitor.py', '3': 'main.py'}
script = scripts.get(choice)

if not script:
    print("Invalid choice.")
    sys.exit(1)

script_path = os.path.join(_HERE, script)
process = subprocess.Popen([sys.executable, script_path])
print(f"\n{script} started. Type 'restart' to restart or 'stop' to quit.\n")

while True:
    try:
        cmd = input().strip().lower()
        if cmd == 'restart':
            process.terminate()
            process.wait()
            process = subprocess.Popen([sys.executable, script_path])
            print(f"{script} restarted.")
        elif cmd in ('stop', 'exit', 'quit'):
            process.terminate()
            print("Stopped.")
            break
    except KeyboardInterrupt:
        process.terminate()
        break
