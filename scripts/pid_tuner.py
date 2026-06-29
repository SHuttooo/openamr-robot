#!/usr/bin/env python3
"""Interactive motor tuner with live step-response plotting — two modes.

Runs on the PC. Talks to the Teensy firmware (via the micro-ROS agent):
  - /debug/tune   (geometry_msgs/Twist)   linear=(Kp,Ki,Kd), angular.x=right-wheel gain -> LIVE update
  - /cmd_vel      (geometry_msgs/Twist)   PID-mode step (linear.x = m/s)
  - /debug/openloop (geometry_msgs/Vector3) open-loop step (x = PWM, NO PID), right scaled by R-gain
  - /debug/left   (geometry_msgs/Vector3) x=target rpm, y=measured rpm   (MOTOR1 = LEFT)   [BEST_EFFORT]
  - /debug/right  (geometry_msgs/Vector3) x=target rpm, y=measured rpm   (MOTOR2 = RIGHT)  [BEST_EFFORT]

TWO MODES (radio, top-left):
  - "Open-loop (gain)": Step sends a fixed PWM to both wheels (PID bypassed). Right = PWM x R-gain.
    Use it to set R-gain so the two wheels overlap — pure hardware response, no PID masking.
  - "PID": Step sends a velocity step (closed loop). Use it to tune Kp/Ki/Kd.

Buttons: Apply (push gains live) · Step (run step + plot both wheels) · Save (write gains to firmware
config on the Pi, for the next reflash). Lift the robot (wheels in the air) before Step.

Usage (PC, ROS sourced, ROS_DOMAIN_ID matching the robot):  python3 pid_tuner.py
"""
import math
import threading
import time
import subprocess

import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, RadioButtons

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data       # BEST_EFFORT — matches the firmware /debug/* topics
from geometry_msgs.msg import Twist, Vector3

PI_HOST = 'botshare@172.17.201.29'
CONFIG = '~/linorobot2_hardware/config/lino_base_config.h'

INIT = dict(kp=2.0, ki=0.10, kd=0.10, gain=1.00, speed=0.15, pwm=150.0, kff=7.87, dith=0.0)
STEP_DURATION = 2.5
STEP_RATE_HZ = 20.0
PWM_MAX = 1023.0        # firmware PWM_BITS=10 -> full-scale PWM (lino_base_config.h)
SMOOTH_WIN = 7          # moving-average window for the rpm plot (firmware rpm is quantized)
WHEEL_DIAMETER = 0.2    # m (lino_base_config.h) -> convert the PID speed command m/s <-> wheel rpm


def ms_to_rpm(v):
    """Straight-line wheel rpm for a robot speed v (m/s): v / (pi*D) * 60."""
    return v * 60.0 / (math.pi * WHEEL_DIAMETER)


def smooth(y, w=SMOOTH_WIN):
    """Centered moving average — turns the quantized rpm staircase into a readable trend."""
    if len(y) < 2 or w < 2:
        return list(y)
    out = []
    for i in range(len(y)):
        a = max(0, i - w // 2)
        b = min(len(y), i + w // 2 + 1)
        out.append(sum(y[a:b]) / (b - a))
    return out


class Tuner(Node):
    def __init__(self):
        super().__init__('pid_tuner')
        self.tune_pub = self.create_publisher(Twist, '/debug/tune', 10)
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.ol_pub = self.create_publisher(Vector3, '/debug/openloop', 10)
        # BEST_EFFORT to match the firmware publishers (else no data is received)
        self.create_subscription(Vector3, '/debug/left', self._left_cb, qos_profile_sensor_data)
        self.create_subscription(Vector3, '/debug/right', self._right_cb, qos_profile_sensor_data)
        self.create_subscription(Vector3, '/debug/pwm', self._pwm_cb, qos_profile_sensor_data)
        self.lock = threading.Lock()
        self.recording = False
        self.t0 = 0.0
        self.buf = dict(lt=[], lv=[], rt=[], rv=[], ltar=[], pt=[], plv=[], prv=[])

    def _left_cb(self, m):
        if self.recording:
            with self.lock:
                self.buf['lt'].append(time.time() - self.t0)
                self.buf['lv'].append(m.y)
                self.buf['ltar'].append(m.x)

    def _right_cb(self, m):
        if self.recording:
            with self.lock:
                self.buf['rt'].append(time.time() - self.t0)
                self.buf['rv'].append(m.y)

    def _pwm_cb(self, m):
        if self.recording:
            with self.lock:
                self.buf['pt'].append(time.time() - self.t0)
                self.buf['plv'].append(m.x)   # left PWM output
                self.buf['prv'].append(m.y)   # right PWM output

    def apply_gains(self, kp, ki, kd, gain, kff, dither):
        msg = Twist()
        msg.linear.x, msg.linear.y, msg.linear.z = float(kp), float(ki), float(kd)
        msg.angular.x = float(gain)         # right-wheel PWM scale
        msg.angular.y = float(kff)          # velocity feedforward gain (PWM/rpm)
        msg.angular.z = float(dither)       # anti-stiction dither amplitude (PWM)
        self.tune_pub.publish(msg)

    def run_step(self, mode, speed, pwm, duration):
        """Blocking step. mode 'pid' -> /cmd_vel (m/s) ; mode 'open' -> /debug/openloop (PWM).
        duration = step length in seconds (chosen on the GUI)."""
        with self.lock:
            for k in self.buf:
                self.buf[k] = []
        self.t0 = time.time()
        self.recording = True
        dt = 1.0 / STEP_RATE_HZ
        n = int(float(duration) * STEP_RATE_HZ)
        for _ in range(n):
            if mode == 'pid':
                c = Twist(); c.linear.x = float(speed); self.cmd_pub.publish(c)
            else:
                v = Vector3(); v.x = float(pwm); self.ol_pub.publish(v)
                # feed the firmware cmd_vel watchdog (200 ms) so moveBase doesn't fullStop;
                # ol_active still bypasses the PID, so the wheels run at the open-loop PWM.
                self.cmd_pub.publish(Twist())
            time.sleep(dt)
        # stop
        for _ in range(5):
            if mode == 'pid':
                self.cmd_pub.publish(Twist())
            else:
                self.ol_pub.publish(Vector3())
            time.sleep(0.02)
        self.recording = False
        with self.lock:
            return {k: list(v) for k, v in self.buf.items()}


def main():
    rclpy.init()
    node = Tuner()
    threading.Thread(target=rclpy.spin, args=(node,), daemon=True).start()

    fig, ax = plt.subplots(figsize=(10, 8))
    plt.subplots_adjust(left=0.1, bottom=0.53, right=0.97, top=0.93)
    ax.set_xlabel('time (s)'); ax.set_ylabel('wheel speed (rpm)')
    ax.set_title('Pick a mode, lift the robot, press "Step"')
    ax.grid(True, alpha=0.3)
    ax2 = ax.twinx()                                  # right axis: the PID PWM output
    ax2.set_ylabel('PWM output (0-1023)', color='gray')

    col = 'lightgoldenrodyellow'
    s_kp = Slider(plt.axes([0.30, 0.48, 0.6, 0.022], facecolor=col), 'Kp', 0.0, 20.0, valinit=INIT['kp'])
    s_ki = Slider(plt.axes([0.30, 0.45, 0.6, 0.022], facecolor=col), 'Ki', 0.0, 10.0, valinit=INIT['ki'])
    s_kd = Slider(plt.axes([0.30, 0.42, 0.6, 0.022], facecolor=col), 'Kd', 0.0, 3.0, valinit=INIT['kd'])
    s_gn = Slider(plt.axes([0.30, 0.39, 0.6, 0.022], facecolor=col), 'R-gain', 0.8, 1.3, valinit=INIT['gain'])
    s_kff = Slider(plt.axes([0.30, 0.36, 0.6, 0.022], facecolor=col), 'Kff (PWM/rpm)', 0.0, 15.0, valinit=INIT['kff'])
    s_dith = Slider(plt.axes([0.30, 0.33, 0.6, 0.022], facecolor=col), 'Dither (PWM)', 0.0, 100.0, valinit=INIT['dith'])
    s_sp = Slider(plt.axes([0.30, 0.30, 0.6, 0.022], facecolor=col), 'speed m/s (PID)', 0.0, 0.50, valinit=INIT['speed'])
    # show the speed command in BOTH m/s and the equivalent wheel rpm on the right
    def _show_speed_rpm(v):
        s_sp.valtext.set_text(f'{v:.2f} m/s = {ms_to_rpm(v):.1f} rpm')
    s_sp.on_changed(_show_speed_rpm)
    _show_speed_rpm(s_sp.val)
    s_pw = Slider(plt.axes([0.30, 0.27, 0.6, 0.022], facecolor=col), 'PWM (open-loop)', 0.0, PWM_MAX, valinit=INIT['pwm'])
    s_dur = Slider(plt.axes([0.30, 0.24, 0.6, 0.022], facecolor=col), 'duration (s)', 0.5, 15.0, valinit=STEP_DURATION)

    radio = RadioButtons(plt.axes([0.04, 0.13, 0.22, 0.07], facecolor=col),
                         ('Open-loop (gain)', 'PID'), active=0)

    b_apply = Button(plt.axes([0.10, 0.04, 0.22, 0.06]), 'Apply gains', color='lightblue')
    b_step = Button(plt.axes([0.39, 0.04, 0.22, 0.06]), 'Step', color='lightgreen')
    b_save = Button(plt.axes([0.68, 0.04, 0.22, 0.06]), 'Save to firmware', color='salmon')

    def mode():
        return 'open' if radio.value_selected.startswith('Open') else 'pid'

    def do_apply(_=None):
        node.apply_gains(s_kp.val, s_ki.val, s_kd.val, s_gn.val, s_kff.val, s_dith.val)
        ax.set_title(f'Applied  Kp={s_kp.val:.2f} Ki={s_ki.val:.2f} Kd={s_kd.val:.3f} '
                     f'R={s_gn.val:.2f} Kff={s_kff.val:.1f} dith={s_dith.val:.0f}')
        fig.canvas.draw_idle()

    def do_step(_=None):
        do_apply()
        m = mode()
        ax.set_title(f'Running {m} step...'); fig.canvas.draw_idle(); fig.canvas.flush_events()
        d = node.run_step(m, s_sp.val, s_pw.val, s_dur.val)
        ax.clear(); ax.grid(True, alpha=0.3)
        ax.set_xlabel('time (s)'); ax.set_ylabel('wheel speed (rpm)')
        ax2.clear(); ax2.set_ylabel('PWM output (0-1023)', color='gray')
        if m == 'pid':
            # the COMMAND: a straight horizontal line at the speed you asked for, in rpm —
            # this is where both wheels are supposed to reach.
            cmd_rpm = ms_to_rpm(s_sp.val)
            ax.axhline(cmd_rpm, color='green', lw=1.8, alpha=0.85,
                       label=f'command {s_sp.val:.2f} m/s = {cmd_rpm:.1f} rpm')
            if d['ltar']:
                ax.plot(d['lt'], d['ltar'], 'k--', lw=1, alpha=0.4)
        # raw quantized samples, faint — and the smoothed trend, bold
        ax.plot(d['lt'], d['lv'], color='tab:blue', lw=0.6, alpha=0.25)
        ax.plot(d['rt'], d['rv'], color='tab:red', lw=0.6, alpha=0.25)
        ax.plot(d['lt'], smooth(d['lv']), color='tab:blue', lw=2, label='LEFT (motor1)')
        ax.plot(d['rt'], smooth(d['rv']), color='tab:red', lw=2, label='RIGHT (motor2)')
        # PWM OUTPUT (what the PID actually sends to the drivers) on the right axis. If it pins to
        # ~1023, the controller is saturated -> the wheels can't go faster (hardware limit).
        if d['plv']:
            ax2.plot(d['pt'], smooth(d['plv']), color='tab:cyan', lw=1.2, ls=':', label='PWM out L')
            ax2.plot(d['pt'], smooth(d['prv']), color='magenta', lw=1.2, ls=':', label='PWM out R')
            ax2.axhline(PWM_MAX, color='gray', lw=0.8, ls='--', alpha=0.5)  # saturation ceiling
            ax2.set_ylim(0, PWM_MAX * 1.05)
        l1, lab1 = ax.get_legend_handles_labels()
        l2, lab2 = ax2.get_legend_handles_labels()
        ax.legend(l1 + l2, lab1 + lab2, loc='lower right', fontsize=8)
        npts = len(d['lv'])
        amp = f"PWM={s_pw.val:.0f}" if m == 'open' else f"speed={s_sp.val:.2f}"
        ax.set_title(f'[{m}] {amp}  R={s_gn.val:.2f} Kff={s_kff.val:.1f}  Kp={s_kp.val:.2f} '
                     f'Ki={s_ki.val:.2f} Kd={s_kd.val:.3f}   ({npts} pts)')
        if npts == 0:
            ax.set_title(f'[{m}] NO DATA — wheels not turning? robot powered + lifted? amplitude > 0?')
        fig.canvas.draw_idle()

    def do_save(_=None):
        cmds = (f'sed -i "s/#define K_P .*/#define K_P {s_kp.val:.3f}/;'
                f's/#define K_I .*/#define K_I {s_ki.val:.3f}/;'
                f's/#define K_D .*/#define K_D {s_kd.val:.3f}/;'
                f's/#define MOTOR2_GAIN .*/#define MOTOR2_GAIN {s_gn.val:.3f}/" {CONFIG}')
        try:
            subprocess.run(['ssh', '-o', 'BatchMode=yes', PI_HOST, cmds], timeout=15, check=True)
            ax.set_title(f'Saved to firmware config (reflash to persist): Kp={s_kp.val:.2f} '
                         f'Ki={s_ki.val:.2f} Kd={s_kd.val:.3f} R-gain={s_gn.val:.2f}')
        except Exception as e:
            ax.set_title(f'Save FAILED: {e}')
        fig.canvas.draw_idle()

    b_apply.on_clicked(do_apply)
    b_step.on_clicked(do_step)
    b_save.on_clicked(do_save)
    do_apply()
    plt.show()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
