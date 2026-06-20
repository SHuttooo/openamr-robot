#!/bin/bash
# Usage: tune.sh KP KI KD  -> edite lino_base_config, build, flash, relance l'agent
KP=$1; KI=$2; KD=$3
cd ~/linorobot2_hardware/config || exit 1
sed -i "s/^#define K_P .*/#define K_P $KP/; s/^#define K_I .*/#define K_I $KI/; s/^#define K_D .*/#define K_D $KD/" lino_base_config.h
cd ~/linorobot2_hardware/firmware || exit 1
ROS_DISTRO=jazzy ~/.platformio/penv/bin/pio run -e teensy40 > /tmp/build.log 2>&1 || { echo "BUILD_FAIL"; tail -4 /tmp/build.log; exit 1; }
pkill -f "[m]icro_ros_agent"; sleep 2
HEX=~/linorobot2_hardware/firmware/.pio/build/teensy40/firmware.hex
echo admin | sudo -S teensy_loader_cli --mcu=TEENSY40 -s -w "$HEX" > /tmp/flash.log 2>&1
grep -q Booting /tmp/flash.log || echo admin | sudo -S teensy_loader_cli --mcu=TEENSY40 -w "$HEX" >> /tmp/flash.log 2>&1
if ! grep -q Booting /tmp/flash.log; then echo "FLASH_FAIL"; tail -3 /tmp/flash.log; exit 1; fi
nohup setsid bash -c "source /opt/ros/jazzy/setup.bash && source ~/linorobot2_ws/install/setup.bash && exec ros2 run micro_ros_agent micro_ros_agent serial -b 115200 -D /dev/serial/by-id/usb-Teensyduino_USB_Serial_16778200-if00" > ~/agent.log 2>&1 < /dev/null & disown
sleep 8
echo "session: $(grep -c 'session established' ~/agent.log) | FLASHED KP=$KP KI=$KI KD=$KD"
