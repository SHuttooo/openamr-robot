# Power & electrical safety

*Last updated: 2026-06-17.*

## Power architecture
| Element | Supply |
|---|---|
| Motors / drivers | **24 V DC** (`DC+ / DC−` on each driver, with a fuse) |
| 24 V source | **battery pack** (lead-acid, see below) — or an **AC/DC converter** (230 V mains) for bench tests |
| Teensy | powered over **USB** from the Pi (5 V → 3.3 V on board) |
| Raspberry Pi | its own supply (USB-C, 5 V) |
| LiDAR | powered over its USB (CP2102 adapter) from the Pi |

## Battery pack
- **4 × 12 V lead-acid** batteries (the big black ones).
- Wired **2 in series → 24 V** (one "pair"). With 2 pairs you can make **24 V** (pairs in parallel, more
  capacity) **or 48 V** (pairs in series) — this matches the OpenAMR platform's "24/48 V" spec.
- **In practice we usually run a single pair = 24 V.**
- ⚠️ Lead-acid basics: respect polarity, don't short the terminals (very high current), charge with a
  suitable lead-acid charger, and don't fully deep-discharge them (shortens life).

The Teensy sends only **low-current logic signals** to the drivers; the **24 V power** goes through the
drivers to the motor phases. Logic ground (Teensy GND) and driver `COM` must be **common**.

## ⚠️ Electrical safety — 230 V AC (read this)
The 24 V side is low-risk, but the **AC/DC converter is fed by 230 V AC, which is potentially lethal.**

- Touching exposed 230 V can cause cardiac fibrillation, "can't-let-go" muscle tetany, burns. ~30 mA
  through the body is already dangerous.
- If the converter's mains terminals are exposed/unprotected, **treat it as dangerous** and let nobody
  touch it while powered.

**Minimum protections (in priority order):**
1. **30 mA RCD / residual-current device** upstream — the single most important life-saver (cuts power in
   milliseconds on a ground/body leak).
2. **Enclose all 230 V wiring** in a closed box — no bare mains conductor reachable by a finger.
3. **Earth** the converter's metal chassis (protective conductor).
4. **Fuse / breaker** on the mains input (short-circuit / overload).
5. **Strain relief** on the mains cable; prefer an IEC inlet over flying leads.
6. **Golden rule**: cut/unplug the mains **before** touching anything on the power side. Never work live.

## Stopping the robot quickly (test safety)
- Software: stop publishing `/cmd_vel` → firmware zeroes motors after 200 ms (watchdog). `Ctrl-C` on the
  publisher works too.
- Hardware backstop: keep a hand on the **24 V cut-off** during powered tests. Wheels off the ground.

## TODO / to document
- Exact battery capacity (Ah) & charger, AC/DC converter model, fuse rating, and whether a physical
  **E-stop** exists (a ROS-independent emergency stop is recommended).
- A **battery voltage monitor** would be useful (lead-acid sags under load; low voltage → erratic motors).
