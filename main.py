"""BATTLE-PY entry point and diagnostics.

python main.py               Launch game
python main.py --self-check  Run asset/flight-physics tests without Panda3D
python main.py --diagnose    Launch and automatically enter combat after startup
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def write_boot_error(trace):
    log=ROOT/'battle-py-error.log'
    try:
        log.write_text(trace,encoding='utf8')
    except OSError:
        log=Path.home()/'battle-py-error.log'
        try:log.write_text(trace,encoding='utf8')
        except OSError:pass
    return log


def self_check():
    import unittest
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_*.py')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def main():
    if '--self-check' in sys.argv:
        return self_check()
    try:
        from panda3d.core import loadPrcFileData
    except ImportError:
        print('Panda3D is not installed for this Python interpreter.')
        print('To install:  python -m pip install -r requirements.txt')
        print('To test without Panda3D:  python main.py --self-check')
        return 1
    loadPrcFileData('', '\n'.join((
        'window-title BATTLE-PY - The Wraith Protocol',
        'win-size 1280 720',
        'fullscreen 0',
        'sync-video 1',
        'framebuffer-multisample 1',
        'multisamples 4',
        'show-frame-rate-meter 0',
        'textures-power-2 none',
        'audio-library-name p3openal_audio',
    )))
    try:
        from battlepy.game import BattlePy
        app=BattlePy()
        if '--diagnose' in sys.argv:
            # A deterministic simulation of the user's ENTER-key startup action.
            from direct.task import Task
            def begin(task):
                print('[DIAGNOSE] Starting mission...',flush=True)
                app.deploy()
                return Task.done
            def finish(task):
                print(f'[DIAGNOSE] State={app.state}; waves={app.wave}; '
                      f'world_tiles={len(app.world.tiles)}',flush=True)
                app.diagnostic_failed = app.state == 'error'
                if app.diagnostic_failed:
                    print('[DIAGNOSE] FAILED: see battle-py-error.log for the original traceback.',
                          flush=True)
                else:
                    print('[DIAGNOSE] Completed without a Python gameplay exception.',flush=True)
                app.userExit()
                return Task.done
            app.taskMgr.doMethodLater(.6,begin,'diagnose-deploy')
            app.taskMgr.doMethodLater(6.0,finish,'diagnose-finish')
        app.run()
        return 1 if getattr(app, 'diagnostic_failed', False) else 0
    except BaseException as exc:
        trace=traceback.format_exc()
        log=write_boot_error(trace)
        print('\nBATTLE-PY encountered a startup/runtime error:',file=sys.stderr)
        print(trace,file=sys.stderr)
        print(f'Full error details: {log}',file=sys.stderr)
        print('The game is not supposed to silently close. The log will help diagnose it.',
              file=sys.stderr)
        return 1


if __name__=='__main__':
    sys.exit(main())
