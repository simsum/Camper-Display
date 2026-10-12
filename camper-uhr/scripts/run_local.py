"""Local development: separate data, loopback HTTP, simulated display hardware."""
import argparse
import os
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    # Never inherit a production data path or hardware adapter from the shell.
    data = ROOT / '.local' / 'data'
    os.environ['CAMPERDISPLAY_DATA_DIR'] = str(data)
    os.environ['CAMPERDISPLAY_VACATION_DB'] = str(data / 'camperdisplay.db')
    os.environ.pop('CAMPERDISPLAY_BACKLIGHT_DIR', None)
    sys.path.insert(0, str(ROOT / 'backend'))

    import settings_store
    from models import Settings
    if not settings_store.DB_PATH.exists():
        settings_store.save_settings(Settings(
            gpsd_host='127.0.0.1', display_schedule_enabled=False,
        ))

    import display_scheduler
    import gps_client
    import uvicorn
    from main import app

    def simulated_power(turn_on):
        display_scheduler._state['display_on'] = turn_on
        display_scheduler._state['brightness_control'] = 'software'

    # Keep application state machines, but do not access router or Linux hardware.
    display_scheduler._set_display_power = simulated_power
    display_scheduler.start_touch_watch_thread = threading.Event
    gps_client.start_background_thread = threading.Event
    print(f'Local data: {data}', flush=True)
    print('GPS: use Settings > Tests. Display power is simulated.', flush=True)
    uvicorn.run(app, host='127.0.0.1', port=args.port)


if __name__ == '__main__':
    main()
