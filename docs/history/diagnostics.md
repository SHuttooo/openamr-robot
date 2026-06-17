# Diagnostics & decisions (the "why")

*Last updated: 2026-06-17.*

A log of the main problems solved and **how** we reasoned, so newcomers understand why the robot is set
up the way it is. Method used throughout: **the LEFT wheel is the reference** (same firmware/gains, so any
asymmetry localizes the fault to the right channel), and **each hypothesis has a distinct data signature**
(we design a test whose result can only match one cause).

---

## 1. "Right wheel runs away / robot doesn't go straight"

### Initial (wrong) hypothesis: right encoder dead
The brief assumed the right encoder was dead (PID windup → runaway). **Refuted:**
- **Test A** (hand-spin each wheel, reconstruct per-wheel speed from `/odom/unfiltered`): both wheels
  produced a signal → both encoders count.
- **Sign test** (roll each wheel forward): both read **positive** → encoder direction correct.
- Later, raw counts (`/debug/*`) confirmed the right encoder reads real motion cleanly under power.

### Root cause #1: driver VAR pot at maximum
Powered test (small `/cmd_vel`, logging `/debug/*`): at nearly equal PWM, **LEFT did 9 rpm, RIGHT did 73 rpm**.
Comparing the only adjustable difference between channels: DIP switches identical, but the **VAR
potentiometer** (speed/gain) was at **10/10** on the right vs **3.5/10** on the left. Lowering the right
VAR to match → the gross runaway disappeared (causal proof: change the cause, change the effect).

### Root cause #2: driver ACC/DEC pot at 0
A residual remained: the right wheel still jerked sporadically (sudden ±50–130 rpm excursions) even after
the VAR fix and after adding PID anti-windup. A **50 Hz capture** around a jerk showed the right counts
moving **coherently** (real oscillation), not isolated spikes → not an encoder glitch; it was a **closed-
loop instability**. An **open-loop test** (`/debug/openloop`, same fixed PWM both wheels, PID bypassed)
showed **both wheels perfectly smooth** → the right *hardware* is healthy; the jerk only happens with the
PID active. Then we found the second pot: each driver has **two** pots, and the **ACC/DEC** (accel ramp)
was **0/10** on the right vs **4/10** on the left. With no ramp, every PID micro-correction hit the motor
abruptly → oscillation. Setting the right ACC/DEC to **4** (matching left) → **fixed**: an 8 s closed-loop
test ran with no jerk.

### Firmware side-fixes (made the loop more robust)
- Added **anti-windup** to the PID (the upstream `pid.cpp` had none — the integral was unbounded).
- Lowered `K_I` (0.4 → 0.15) to damp the loop.

### Takeaway
The fault was **100 % motor-driver configuration** (two pots on the right driver), not the encoders,
wiring, or software. Always check the driver pots/DIP match between left and right.

---

## 2. "IMU doesn't work" → it was the wrong chip

Enabling `USE_MPU6050_IMU` made `setup()` hang (LED 3 blinks, no topics). We wrote a tiny **I²C scanner**
(`~/i2cscan`): a device answers at **0x68**, but `WHO_AM_I = 0x70`. A real MPU6050 returns 0x68; **0x70 is
an MPU6500**. The board labeled "MPU6050" is actually an **MPU6500** (common on clones). The MPU6050 driver
rejected it; the **MPU9250 driver accepts it** (it reads WHO_AM_I bits [6:1] = 0x38, which it allows, and
the MPU6500 is register-compatible). Switched config to **`USE_MPU9250_IMU`** → `/imu/data` now reads real
gravity (~9.74 m/s² on z). Hardware/wiring were fine all along. (Details: [../hardware/imu.md](../hardware/imu.md).)

---

## 3. Build/flash toolchain on the Pi (Ubuntu 24.04)

Setting up PlatformIO on a PEP 668 ("externally managed") Ubuntu was non-trivial:
- PlatformIO installed **inside its own venv** (`~/.platformio/penv`) so its internal `pip install`s
  (colcon, empy, lark…) aren't blocked by PEP 668. The penv was created with `virtualenv` (system
  `python3-venv` was missing).
- Flashing: `teensy_loader_cli` (`sudo apt install teensy-loader-cli`) + PJRC udev rules in
  `/etc/udev/rules.d/00-teensy.rules`. The reliable flash is `sudo teensy_loader_cli --mcu=TEENSY40 -s -w`
  (soft reboot); if the write races, retry `-w` once it's in HalfKay.
- `pkill -f micro_ros_agent` **self-matches** its own command line (kills the SSH shell, exit 255) → use
  `pkill micro_ros_agent` (by process name).

---

## 4. Other notes
- **LiDAR**: killing the driver brutally mid-scan leaves it stuck (`80008000`/timeout) → unplug/replug.
- **IMU not fused yet**: `/odom` is wheel-only; the (now working) IMU should be fused via an EKF later for
  less heading drift.
- **Geometry**: real robot Ø0.2 / separation 0.45 (the sim uses 0.22 / 0.4075) — calibrate odometry on the
  real robot.
