import sys
import os

# Adding the root directory to the path so we can import the Loom Kernel
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from core.kernel.handshake import LoomKernel

def run_buyer_agent():
    """
    Simulates a 3rd-party AI Agent (e.g., a Shopping Assistant) 
    integrating with the Loom Protocol.
    """
    loom = LoomKernel()
    
    print("--- [Agentic Shopping Assistant Started] ---")
    
    # 1. The Agent defines its intent
    my_intent = "Purchase 1x Microsoft Surface Pro 11 - Platinum"
    
    # 2. The Agent generates a unique Intent Hash for the Loom Ledger
    # In a real app, this would be a SHA-256 of the specific product ID + timestamp
    target_resource_hash = "MS-SURFACE-PR11-PLT-001"
    
    print(f"Agent Intent: {my_intent}")
    
    # 3. The Agent performs the Loom Handshake
    # This replaces a standard 'Insecure' API call
    request_packet = {
        "agent_id": "SHOP-BOT-USR-4421",
        "intent": my_intent,
        "intent_hash": target_resource_hash,
        "expiry": 5000 # 5 second atomic lock
    }
    
    print("Initiating Loom ATP Handshake...")
    response = loom.process_handshake(request_packet)
    
    # 4. Agent reacts to the Protocol's Atomic Finality
    if response["status"] == 201:
        print(f"SUCCESS: {response['message']}")
        print("Agent Action: Proceeding to encrypted checkout.")
    else:
        print(f"FAILURE: {response['message']}")
        print("Agent Action: Conflict detected. Retrying with alternative vendor...")

if __name__ == "__main__":
    run_buyer_agent()