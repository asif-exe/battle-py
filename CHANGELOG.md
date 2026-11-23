# Changelog

## 1.3.0 — Air Superiority Update

- **Dedicated Q exit key** from every game state, with the best score saved.
- Four distinct hostile aircraft classes: scouts, high-agility interceptors, strike fighters and recurring elite aces.
- Procedural VIGIL anti-aircraft sites spawn on island terrain and engage the player.
- Tracking enemy missiles, countermeasure decoys (`C`), a recharge meter, and missile warnings.
- Manual threat selection (`Tab`), cannon lead indicator, tactical radar blips, and ace boss-health display.
- Predictive hostile cannon fire, evasive manoeuvres, and greater variety between early and later waves.
- Kill-chain score bonuses, hit confirmation, air/ground kill credit, and sector-clear rewards.
- Laptop-friendly weapon hotkeys (`J` gun, `K` missile), preserving existing mouse controls.
- Five additional original synthesized sound effects: incoming, flare, hit, boss and combo.
- Expanded GPU-free regression tests for combat mathematics, key handling and real flare spawning.
- First-time Linux installer using a local Python virtual environment.


## 1.2.1 — Flight Startup Hotfix

- Corrected `key_y` to `key_yaw` in the live flight steering calculation. This resolves the reported `NameError` immediately after pressing Enter in v1.2.
- Added headless tests that run the *actual* flight-update method for keyboard steering, mouse steering, afterburner, normal flight and surface-impact handling.
- Suppressed duplicate identical gameplay error reports while the error panel is already active, while allowing logging after a redeploy/retry.
- The `--diagnose` mode now exits with an error code when gameplay enters the error state, instead of reporting success after an in-game exception.
- All v1.2 combat, crash, ejection, sound, and environment features remain included.

## 1.2 — Crash & Survival Update

- Guarded Enter-key event handlers and gameplay callbacks; surfaced runtime errors in-game instead of letting the game loop immediately exit.
- Persistent text traceback at `battle-py-error.log`, retained console output, and an automated `--diagnose` startup test.
- New impact model for terrain, sea, air-to-air collisions, and structural damage.
- Crash sequence with separated debris, physics, sparks, smoke, water foam, camera shake, and mission results.
- Progressive engine smoke, low-hull fire, warning alarm, and damage tint.
- Emergency pilot ejection and parachute animation (E).
- Five new procedural WAV effects: crash, splash, fire, eject, alarm.
- New F8/F9 crash and damage showcase shortcuts.
- Clean restart to combat or title screen after a loss.
- Expanded dependency-free test suite covering impact physics and the actual Enter callback code.

## 1.0 — Initial Python Edition

- Procedural terrain and sea, AX-9 Wraith 3D model, enemy waves, cannon and missile combat.
- Multilayer reactive engine/wind/afterburner sound, HUD, scores and launch scripts.
