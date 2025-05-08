try:
    while True:
        try:
            ROLE  = "relay"
            import os
            import sys
            sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))
            sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

            from  MAC import MAC_RX_1D, MAC_TX_1D


            

            while True:
                phase = 1
                rx = MAC_RX_1D(ROLE=ROLE)
                
                file = rx.record(phase=phase)
                if not file:
                    print(f"failed synchronization {ROLE}, phase_{phase}")
                    # continue

                rx.process_all_frames(file=file, phase=phase)
                rx = None

                # phase = 2
                # tx = MAC_TX_1D(ROLE=ROLE)
                
                # if not tx.transmit():
                #     print(f"failed synchronization {ROLE}, phase_{phase}")
                #     # continue
                # else:
                #     print(f"transmission {ROLE}, phase_{phase} done")
                # tx = None


        except Exception as e:
            print(f"An error occurred: {e}")
            continue
except KeyboardInterrupt:
    print("\nInterrupted by user. Exiting gracefully...")

