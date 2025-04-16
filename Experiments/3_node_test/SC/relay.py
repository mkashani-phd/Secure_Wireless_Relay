try:
    while True:
        try:
            ROLE  = "relay"
            import os
            import sys
            sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))
            sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

            from  MAC import MAC_RX_SC, MAC_TX_SC

            rx = MAC_RX_SC(ROLE=ROLE)
            tx = MAC_TX_SC(ROLE=ROLE)

            

            while True:
                phase = 1
                

                file = rx.record(phase=phase)
                if not file:
                    print(f"failed synchronization {ROLE}, phase_{phase}")
                    # continue

                rx.process_all_frames(file=file, phase=phase)
                rx = None

                phase = 2

                if not tx.transmit():
                    print(f"failed synchronization {ROLE}, phase_{phase}")
                    # continue
                else:
                    print(f"transmission {ROLE}, phase_{phase} done")
                tx = None


        except Exception as e:
            print(f"An error occurred: {e}")
            continue
except KeyboardInterrupt:
    print("\nInterrupted by user. Exiting gracefully...")

