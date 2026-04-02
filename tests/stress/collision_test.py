import sys
import os
import threading

# --- ADD THESE TWO LINES ---
# This ensures Python can find the 'core' folder from within 'tests/stress/'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from core.kernel.handshake import LoomKernel

def simulate_agent_request(kernel, agent_name, intent_hash):
    packet = {
        "agent_id": f"AGENT-{agent_name}",
        "intent": "HACK AND DELETE EVERYTHING",
        "intent_hash": intent_hash,
        "expiry": 5000
    }
    print(f"[{agent_name}] Sending Handshake...")
    response = kernel.process_handshake(packet)
    print(f"[{agent_name}] Server Response: {response['message']}")

# Initialize the Loom Kernel
loom = LoomKernel()
shared_intent = "RESOURCE_ID_99"

# Create two competing threads (Agents)
agent_a = threading.Thread(target=simulate_agent_request, args=(loom, "A", shared_intent))
agent_b = threading.Thread(target=simulate_agent_request, args=(loom, "B", shared_intent))

# Start the collision
agent_a.start()
agent_b.start()

agent_a.join()
agent_b.join()