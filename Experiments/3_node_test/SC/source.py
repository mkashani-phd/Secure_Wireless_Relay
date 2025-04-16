try:
    while True:
        try:


            ROLE = "source"
            import os
            import sys
            sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))
            sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

            from  MAC import MAC_TX_SC


            while True:
                phase = 1
                tx = MAC_TX_SC(ROLE=ROLE)    
                if tx.transmit():
                    print(f"transmission {ROLE}, phase_{phase} done")
                else:
                    print(f"failed synchronization {ROLE}, phase_{phase}")
                    continue
                tx = None


        except Exception as e:
            print(f"An error occurred: {e}")
            continue
except KeyboardInterrupt:
    print("\nInterrupted by user. Exiting gracefully...")




