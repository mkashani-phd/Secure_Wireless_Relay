# Diagrams

Standalone TikZ diagrams documenting the actual TX/RX signal-processing code in `src/`. Each file is self-contained (`\documentclass{standalone}`) — compile directly with `pdflatex <file>.tex`, or paste into a blank Overleaf project.

- **`fsk_modulate.tex`** — flow diagram of `TX.fsk_modulate()` in [`src/tx.py`](../src/tx.py): the two independent CPFSK phase-accumulation pipelines (message frame, and `mac` = tag or keystream) and how they're combined by weighted complex-amplitude superposition inside the message time window only.
- **`rx_pipeline.tex`** — flow chart of the receive pipeline in [`src/rx.py`](../src/rx.py): from `RX.record()` through `frameFinder()`'s amplitude-threshold burst detection, per-symbol demodulation, `detect_message_indices()`'s repetition-code boundary matching, to the final sliced/logged output. Also shows where the MQTT ready/begin handshake (`src/MQTT/mqtt_sync.py`) fits as the coarse synchronization step before recording starts.

Both were verified against the actual source and, for the RX pipeline's frame-boundary detection, against a real raw `.iq` recording reprocessed through the exact algorithm (see the IEEE Data Descriptions paper draft for that figure).
