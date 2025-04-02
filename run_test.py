import os
import threading
import time


# === Thread wrappers ===

def run_tx():
    print("[SOURCE] Transmitting...")
    os.system("python3 3_node_test/tx.py")

def run_rx_dest():
    print("[DESTINATION] Listening for source message...")
    os.system(f"python3 3_node_test/rx.py")

def run_rx_dest_second():
    print("[DESTINATION] Listening for relay message...")
    os.system(f"python3 3_node_test/rx.py")

def run_rx_relay():
    print("[RELAY] Listening for source message...")
    os.system(f"python3 3_node_test/rx_relay.py")

def run_tx_relay():
    print("[RELAY] Transmitting decoded message...")
    os.system(f"python3 3_node_test/tx_relay.py")

# === Main experiment sequence ===

def main():



    # --- Phase 1: At t₀ ---
    # Start destination RX and relay RX
    t_dest_rx1 = threading.Thread(target=run_rx_dest)
    t_relay_rx = threading.Thread(target=run_rx_relay)
    t_source_tx = threading.Thread(target=run_tx)
    

    os.system('uhd_find_devices')
    time.sleep(.7)  # Give some time for the USRP to initialize
    t_dest_rx1.start()
    time.sleep(.7)
    t_relay_rx.start()

    # Slight delay before TX to simulate "source emits during RX window"
    time.sleep(.7)
    t_source_tx.start()

    # Wait for destination RX and relay RX to finish
    t_dest_rx1.join()
    time.sleep(.1)
    t_relay_rx.join()
    time.sleep(.1)
    t_source_tx.join()
    time.sleep(.1)

    #kill the threads
    t_dest_rx1 = None
    t_relay_rx = None
    t_source_tx = None

    print("[INFO] Phase 1 finished.")

    # --- Phase 2: After decoding ---
    # Wait until estimated t2

    time.sleep(3.5)  # Simulate time taken for decoding

    # Start relay TX and destination RX again
    t_dest_rx2 = threading.Thread(target=run_rx_dest_second)
    t_relay_tx = threading.Thread(target=run_tx_relay)

    t_dest_rx2.start()
    time.sleep(2.5)  # Let destination start listening
    t_relay_tx.start()

    t_dest_rx2.join()
    time.sleep(.1)
    t_relay_tx.join()
    time.sleep(.1)
    
    #kill the threads
    t_dest_rx2 = None
    t_relay_tx = None
    print("[INFO] Phase 2 finished.")


    print("[INFO] Experiment finished.")

if __name__ == "__main__":

    # for i in range(3):
        main()
