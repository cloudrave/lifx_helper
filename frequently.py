#!/home/ubuntu/scripts/lifx/venv/bin/python3

"""
Control LIFX bulbs according to schedules.
"""
import json
import traceback
from datetime import datetime

import os
import pifx
import time

ABS_DIR = os.path.dirname(os.path.abspath(__file__))

"""
secrets.json spec:
{
    "API_KEY": string,
    "HOME_NETWORK_SSID": string or array of strings
}
"""
with open(os.path.join(ABS_DIR, 'secrets.json')) as secrets_file:
    secrets = json.load(secrets_file)

api = pifx.PIFX(
    api_key=secrets['LIFX_API_KEY']
)

# Force this to be an array of SSIDs.
home_network_ssid_list = secrets['HOME_NETWORK_SSID']
if not isinstance(home_network_ssid_list, list):
    home_network_ssid_list = [home_network_ssid_list]


def main():
    with open(os.path.expanduser('~/check_in.json')) as f:
        check_in_info = json.load(f)['data']

    # Get basic info.
    last_check_in_time = datetime.utcfromtimestamp(check_in_info['check_in_time'])
    seconds_since_last_check_in = \
        int((datetime.utcnow() - last_check_in_time).total_seconds())
    minutes_since_last_check_in = round(seconds_since_last_check_in / 60, 1)
    last_check_in_ssid = check_in_info['ssid']
    last_check_in_ip = check_in_info['ip']
    log("""Latest Check-in at {time} ({minutes} minutes ago). """.format(
        time=last_check_in_time.isoformat(),
        minutes=minutes_since_last_check_in
    ) +
        """SSID: "{}". """.format(last_check_in_ssid) +
        """IP: "{}".""".format(last_check_in_ip)
    )

    # If haven't checked in recently at home, turn off lights.
    if (not(
        last_check_in_ssid in home_network_ssid_list and
        minutes_since_last_check_in <= 60
    )):
        warn_and_then_turn_lights_off_slowly()


def warn_once(warn_speed):
    api.state_delta('all', brightness=-0.3, duration=warn_speed)
    time.sleep(warn_speed)
    api.state_delta('all', brightness=0.3, duration=warn_speed)
    time.sleep(warn_speed)
    log("Warned once.")


def turn_off_slowly(duration=10):
    api.state_delta('all', power='off', duration=duration)
    time.sleep(duration)
    log("Turned off slowly.")


def are_any_lights_on():
    for light in api.list_lights():
        if light['power'] == 'on':
            return True
    return False


def warn_and_then_turn_lights_off_slowly():
    # Skip if lights are already off.
    if not are_any_lights_on():
        log("Lights are already off. No need to turn them off again.")
        return
    # Perform the actual action.
    [warn_once(warn_speed=2) for _ in range(2)]
    turn_off_slowly()


def log(message):
    with open(os.path.join(ABS_DIR, "frequently.log"), "a") as log_file:
        log_file.write("[{}]: {}\n".format(datetime.utcnow().isoformat(), message))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # Log the exception.
        tb = traceback.format_exc()
        log(tb)
        # Re-raise the exception.
        raise
