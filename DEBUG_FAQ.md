# gps-attack Debugging FAQ

# Reverting Ardupilot Back to Normal (Removing Persisted Parameters)

tl;dr Run this easy-to-use script to delete Ardupilot run artifacts:

```bash
./clear_persistent.sh
```

A longer explanation for reverting Ardupilot is provided below.

## Step 1: Stop SITL

Hit `Ctrl+C` in the `sim_vehicle.py` terminal (if you're currently running any of the `gps-attack` tests).

## Step 2: Delete `eeprom.bin`

It contains all the persisted parameters in Ardupilot, so delete the file to return to ArduPilot's factory default settings.

```bash
rm eeprom.bin
```

## Step 3: Clean up MAVProxy run artifacts (optional)

While optional, you can clean up other MAVProxy run artifacts so they don't clutter your view.

```bash
rm -f mav.parm mav.tlog mav.tlog.raw
```

## Step 4: Reluanch SITL:

```bash
sim_vehicle.py -v ArduCopter \
    --out udp:127.0.0.1:14550 \
    --out udp:127.0.0.1:14551
```

Wait for the `EKF3 IMU0 is using GPS` message. Then, open QGroundControl, go to Plan, and open whatever `.plan` file you would like. There should be no persisted gps-attack parameters by this point.

# Setting the Drone to Oak Ridge, TN

If you are testing using only software (rather than a real drone), then the Oak Ridge `.plan` files assume that  the drone location is the following:

```bash
sim_vehicle.py -v ArduCopter \
    --custom-location=35.93051398,-84.31067453,50,0 \
    --out udp:127.0.0.1:14550 \
    --out udp:127.0.0.1:14551
```

Furthermore, the ORNL Conference Parking Lot coordinates are (35.93323230241756, -84.31181199768014). The altitude is set at 50 meters. This is used for the GPS `replay` spoofing attack.