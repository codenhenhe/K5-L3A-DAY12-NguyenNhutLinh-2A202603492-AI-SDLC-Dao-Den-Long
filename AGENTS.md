# Đảo Đèn Lồng

- Read the current lab phase requirements before changing mechanics or the contract.
- Build with `python3 -m compileall -q lantern`. Play with `python3 -m lantern play`.
- Run `sh scripts/verify-phase-1.sh` before calling Phase 1 changes complete. Fix failing checks or report what remains; keep the original generated output.
- `lantern/game.py` holds gameplay for both headless and browser play. Keep the browser responsible for input, rendering, and HUD.
- Treat `game.contract.json` as the source for declared tuning. Preserve the 60 Hz tick and JSONL semantics unless a later ticket changes the contract.
- Keep Phase 1 verification notes in `docs/phase-1.md`; record reasons when later tickets replace existing rules or tests.
