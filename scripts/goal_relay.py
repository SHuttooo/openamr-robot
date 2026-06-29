# ⚠️ LEGACY / OBSOLETE (2026-06-26). Standalone goal forwarder (old field system).
#    Replaced by the integrated brick: openamrobot_bringup/goal_relay.launch.py
#    (or the docking, which acts as the forwarder). See docs/ARCHITECTURE.md §1.5 + §6.
#    Kept until bringall.sh is repointed to bringup.launch.py sim:=false.
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose

class Relay(Node):
    def __init__(self):
        super().__init__("goal_relay")
        self.client = ActionClient(self, NavigateToPose, "/navigate_to_pose")
        self.create_subscription(PoseStamped, "/goal_pose", self.cb, 10)
        self.get_logger().info("Relay /goal_pose -> navigate_to_pose PRET")
    def cb(self, msg):
        if not self.client.wait_for_server(timeout_sec=3.0):
            self.get_logger().error("action server absent")
            return
        g = NavigateToPose.Goal(); g.pose = msg
        self.client.send_goal_async(g)
        self.get_logger().info(f"GOAL envoye: x={msg.pose.position.x:.2f} y={msg.pose.position.y:.2f}")

rclpy.init(); rclpy.spin(Relay())
