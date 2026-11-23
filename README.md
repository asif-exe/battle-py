# BATTLE-PY

**The Wraith Protocol · Version 1.3.0 — Air Superiority Update**

A fast, atmospheric 3D jet combat game built in Python with **Panda3D**. Pilot the AX-9 Wraith over an endless chain of islands, fight escalating squadrons of scouts, interceptors, bombers and elite aces, destroy anti-aircraft installations, and make it home in one piece. Your engine and wind audio respond continuously to the way you fly.

This edition adds **enemy missile attacks, countermeasure flares, dedicated Q-to-quit, smarter dogfighting, ground SAM defenses and ace encounters**, alongside the aircraft destruction and pilot survival system. Hard impacts have consequences. The Wraith can smoke, catch fire, break apart, and hit the sea. You can even eject before the jet is lost.

All models, sounds, landscape meshes, and textures in this project were generated or created for the game. Other than the Panda3D Python engine, it does not download assets, use an online account, or call a server.

## Quick start — Windows

1. Extract the ZIP. Open the `battle-py` folder.
2. Double-click **`install_and_play_windows.bat`** to create a local Python environment, install Panda3D, run tests, and launch the game.
3. On subsequent launches, double-click **`run_windows.bat`**.
4. Press **Enter** on the title screen to deploy. If the game encounters an error, **the launcher leaves its console open**, and the game attempts to display an error panel instead of immediately disappearing.

Requirements: a 64-bit installation of **Python 3.10+**, Windows 10/11, an OpenGL-capable graphics driver, and internet access for the one-time Panda3D installation. Python 3.11 or 3.12 is a good choice if Panda3D wheel availability is a problem on your machine.

### Mac or Linux

Open a terminal in the extracted `battle-py` folder:

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

Alternatively run `./run_mac_linux.sh` after dependencies are installed.

**New Linux first-time launcher (recommended):**

```bash
chmod +x install_and_play_linux.sh
./install_and_play_linux.sh
```

It creates a local `.venv`, installs Panda3D into it, runs the headless tests, and launches BATTLE-PY. For later launches, `source .venv/bin/activate && python main.py` works. On some distributions you must install `python3-venv` first. If you use Conda, you can instead install requirements inside your existing environment and run `python main.py`.

## Controls

| Key | Action |
|---|---|
| **Q** | **Quit the game immediately from any screen** (menu, flight, pause, death or error) |
| **Enter** | Deploy from title / redeploy after defeat |
| **Mouse** | Steer by moving relative to the screen centre |
| **A / D**, left / right arrows | Turn |
| **Up / down arrows** | Climb or dive |
| **W / S** | Increase / decrease throttle |
| **Left click / J** | Fire cannons (heat-limited) |
| **Right click / F / K** | Fire homing Viper missile if locked; otherwise unguided |
| **Tab** | Cycle available air and ground targets; temporarily prioritizes the selected target |
| **C** | Release flare countermeasures to defeat incoming guided missiles (3 charges, regenerating) |
| **Shift** | Afterburner, powered by a rechargeable boost meter |
| **Space** | Barrel roll |
| **V** | Chase / cockpit / orbit camera |
| **E** | **Emergency ejection:** save the pilot, but abandon the aircraft |
| **P / Esc** | Pause and resume |
| **Esc** after crashing | Skip the aftermath or return to the title screen |
| **R** | Redeploy from defeat screen |
| **Backspace** | Return to title from pause/death |
| **M** | Toggle all game audio |
| **F11** | Fullscreen/windowed |

**Optional crash-effect showcase:** During a mission, **F9** simulates major engine damage so you can see the smoke and warning system. **F8** triggers an immediate cinematic airframe failure. These are demonstration shortcuts, not required during normal gameplay.

## NEW in 1.3 — A real dogfight

- **Four air-threat classes:** TALON scouts are quick and fragile, RAPTOR interceptors dogfight and evade, REAPER strike fighters keep their distance and launch missiles, and SPECTRE aces appear in every fourth wave with unique hull shapes and a boss-health bar.
- **Ground anti-aircraft combat:** from wave three, VIGIL SAM stations hide on islands, follow your jet and launch heat-seeking missiles. Strafing guns or missiles can destroy them. Their icons appear on the tactical radar.
- **Actual guided enemy missiles:** missiles turn toward your moving jet instead of travelling straight; a warning sounds and flashes on the HUD. Each weapon has a limited lifetime and can strike terrain.
- **Countermeasures:** hit **C** to eject a six-flare fan. Nearby incoming missiles can be redirected to the decoys; stocks refill over time. You have to time deployment rather than hold C continuously.
- **Manual targeting:** hit **Tab** to cycle threats, including ground sites. The gold lead pip helps you put cannon rounds ahead of a moving fighter. Locked Viper missiles can home on either air or ground targets.
- **Reworked encounters:** aggressive pursuit, predictive hostile cannon fire, rolling evasive aircraft, stronger late-wave lineups, elite encounters, bonus points for consecutive kills, rearm/repair breaks between waves, and new incoming-missile, flare, hit, ace and combo sounds.
- **More readable combat HUD:** tactical blips, threat type, active missile alerts, flare count, hit confirmation, kill chains, and SPECTRE's health bar.
- **Dedicated exit key:** press **Q** at any time. Your best score is saved locally before the window closes.

### Dogfighting tips

Start wave one with cannons; save a Viper missile for an interceptor that is harder to line up. Press Tab to select a specific target, but you still need it inside the lock area to get guidance. Use Shift to close the distance, and release flares only when an incoming missile warning is active. SAM batteries are easier to hit with missiles than with a steep high-speed cannon pass. For trackpads, use **J** to fire and **K** to launch without mouse buttons.

## When the Wraith goes down

- **Terrain:** low-speed scrapes damage your aircraft; high-speed strikes and severe dives cause catastrophic break-up instead of the old automatic bounce. Collision calculations use your airspeed, downward motion, and impact penetration.
- **Ocean:** touching the sea at fighter speeds causes a water strike, followed by a foam ring, splash noise, wreckage, and smoke. Land impact and water impact have different messages and effects.
- **Enemy fire:** the jet develops a smoke trail when damaged. Critical hull status produces engine fire, damage tint, warning alarms, and increasingly unstable engine audio. If hull reaches zero, the Wraith is destroyed.
- **Mid-air collision:** a high-speed collision can destroy the fighter instantly. Slower contact can instead cause substantial structural damage.
- **Destruction cinematic:** detached wings, tail pieces, nose section and engine casings scatter with gravity, rotation, and ground bounces. Fireballs, sparks, smoke, camera shake, and a moving crash camera play before the results screen.
- **Emergency ejection:** press **E** before destruction to launch the pilot's rescue seat. A parachute opens during the sequence. The final screen records that the pilot survived, but the mission and aircraft are lost.
- **Results:** after the cinematic, review the cause of loss, kills, completed wave, points, and personal best. Press **Enter** or **R** to redeploy. There is no need to restart Python.

The game tracks enemy squadrons, anti-aircraft sites, weapon heat, missile rearming, flare supplies, boost energy, hull integrity, targeting, kill chains, and your best score. The record is stored locally at `~/.battle_py_highscore.json`.

## What to do if pressing Enter closes the game

**Fixed in 1.2.1:** The previous 1.2 build had a typo in `battlepy/game.py` inside `_update_flight`: `key_y` was used instead of the existing `key_yaw` variable. That produced a `NameError` as soon as the player pressed Enter to deploy. The actual flight-update method is now covered by headless control-input tests, including neutral, keyboard, mouse, boost, and collision paths. This release also suppresses duplicate identical error messages while the error screen is active.

The gameplay loop and Enter callback remain protected by exception handlers. If a different error occurs, the log and diagnostics can help pinpoint it. No code can completely rule out graphics-driver or native-library crashes on every computer.

1. **Use `run_windows.bat`**, not a direct double-click on `main.py`. It keeps the console open after the process exits.
2. If you see a `GAMEPLAY ERROR` panel, check **`battle-py-error.log`** inside the game folder (or your home folder if the game directory is read-only).
3. From Command Prompt in the game folder, run `python main.py --self-check`. This checks included assets, flight-impact logic, and Enter-callback safety without Panda3D or a graphics window.
4. With Panda3D installed, run `python main.py --diagnose` to **automatically deploy** and run a six-second gameplay check. **This diagnostic closes intentionally after six seconds.** Do not confuse that expected close with a crash.
5. If the process still closes on real gameplay, share the traceback from the console or the contents of `battle-py-error.log`, along with your Python version and whether you have a dedicated GPU. A native GPU driver failure may produce no Python traceback.

Missing Panda3D? Run `python -m pip install -r requirements.txt` with the **same Python installation** that starts the game. If the display is black, update your GPU driver; the water shader has a basic fallback. If FPS is low, change `LOAD_RADIUS = 3` to `2` and `GRID_CELLS = 25` to `18` inside `battlepy/settings.py`, and restart.

## Project structure

```text
battle-py/
├── main.py                      Window configuration, diagnostics, error logging
├── requirements.txt             Panda3D
├── install_and_play_windows.bat  One-click Windows setup and launcher
├── run_windows.bat               Windows launcher (console stays open)
├── run_mac_linux.sh              macOS/Linux launcher
├── battlepy/
│   ├── game.py                  Flight, dogfights, missiles, flares, SAMs, crash states
│   ├── combat.py                Testable wave, hostile and intercept calculations
│   ├── survival.py              Testable collision and damage decisions
│   ├── geometry.py              Original jet/drone/debris/parachute models
│   ├── audio.py                 Movement-sensitive audio, weapons and combat warnings
│   ├── world.py                 Procedural terrain, ocean, sky, clouds
│   ├── hud.py                   Tactical HUD, menus, crash/results screens
│   ├── mathx.py                 Deterministic terrain math
│   └── settings.py              Adjustable balance and visual settings
├── assets/
│   ├── audio/                   17 original synthesized WAV recordings
│   └── textures/                Procedural cloud, sun, and application icon
├── tests/                       No-GPU regression tests (flight + combat)
└── tools/
    ├── build_assets.py          Rebuild original environment textures/sounds
    └── build_crash_audio.py     Rebuild new crash and rescue sounds
```

The existing asset builder requires NumPy and Pillow **only if you want to regenerate artwork**; they are not runtime game dependencies. The crash and combat audio builders require only Python's standard library.

## Testing and limitations

Run the included test suite:

```bash
python main.py --self-check
```

The updated source passes Python compilation, the dependency-free regression tests, and archive-integrity checks. **I could not visually playtest the 3D game here:** Panda3D is not installed and this environment could not download it. The actual OpenGL window, controls, explosion rendering, and your particular Enter-key failure still need to be verified with Panda3D on your computer. The error handling and diagnostic mode are designed to make any remaining problem identifiable rather than silently closing the game.

### Credits

BATTLE-PY was implemented as an original Python interpretation of the earlier Barrel Skies flight project. The 3D models, landscape, shaders, interface, and sound assets were made for this project. Panda3D is a third-party open-source game engine and is not bundled in the ZIP.
