#!/usr/bin/env python3
"""
ROS 2 Car Safety System Node
============================
Implements hands-off detection, health monitoring, long-range collision avoidance,
and emergency handling. All thresholds and behaviour are exposed through the
ROS 2 parameter server and can be changed at runtime.
"""

import math
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rcl_interfaces.msg import SetParametersResult, ParameterDescriptor, FloatingPointRange, IntegerRange
from rcl_interfaces.srv import GetParameters, SetParameters, ListParameters, DescribeParameters

from std_msgs.msg import Float32, Float64, String, Bool, Header
from geometry_msgs.msg import PoseStamped, Twist
from sensor_msgs.msg import NavSatFix
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from std_srvs.srv import Trigger, SetBool


# ---------------------------------------------------------------------------
# Internal enums & simple data holders
# ---------------------------------------------------------------------------

class DriveMode(Enum):
    MANUAL = auto()
    ASSISTED = auto()
    FULL_AUTONOMOUS = auto()


class HealthStatus(Enum):
    NORMAL = auto()
    WARNING = auto()
    CRITICAL = auto()


@dataclass
class Obstacle:
    distance_m: float
    relative_speed_kmh: float
    confidence: float = 0.9
    type: str = "unknown"


# ---------------------------------------------------------------------------
# Main Node
# ---------------------------------------------------------------------------

class CarSafetyNode(Node):
    """ROS 2 node that owns the safety logic and exposes a full parameter server."""

    def __init__(self):
        super().__init__('car_safety_node')

        # 1. Declare all parameters
        self._declare_parameters()

        # Cache frequently used values
        self._load_parameters()

        # 2. Dynamic reconfigure callback
        self.add_on_set_parameters_callback(self._on_parameters_changed)

        # 3. Internal state
        self.drive_mode = DriveMode.MANUAL
        self.pilot_active = False
        self.is_pulled_over = False
        self.hazard_lights = False
        self.current_speed_kmh = 0.0
        self.steering_torque_nm = 5.0
        self.position = (37.7749, -122.4194)
        self.hands_off_start: Optional[float] = None

        self.health = {
            'heart_rate': 72,
            'spo2': 98.0,
            'breathing_rate': 16,
            'bp_sys': 120,
            'bp_dia': 80,
            'fatigue': 0.1,
            'alerts': [],
            'status': HealthStatus.NORMAL,
        }

        self.last_obstacles: List[Obstacle] = []

        # 4. Publishers
        self.pub_mode = self.create_publisher(String, 'safety/drive_mode', 10)
        self.pub_pilot = self.create_publisher(Bool, 'safety/pilot_active', 10)
        self.pub_hazard = self.create_publisher(Bool, 'safety/hazard_lights', 10)
        self.pub_cmd_vel = self.create_publisher(Twist, 'safety/cmd_vel', 10)
        self.pub_event = self.create_publisher(String, 'safety/events', 10)
        self.pub_diagnostics = self.create_publisher(DiagnosticArray, 'diagnostics', 10)
        self.pub_emergency = self.create_publisher(String, 'safety/emergency', 10)

        # 5. Subscribers
        self.create_subscription(Float32, 'vehicle/steering_torque', self._cb_steering, 10)
        self.create_subscription(Float32, 'vehicle/speed', self._cb_speed, 10)
        self.create_subscription(NavSatFix, 'vehicle/gps', self._cb_gps, 10)
        self.create_subscription(String, 'health/watch_data', self._cb_health, 10)
        self.create_subscription(String, 'perception/obstacles', self._cb_obstacles, 10)

        # 6. Services
        self.create_service(Trigger, 'safety/force_pullover', self._srv_force_pullover)
        self.create_service(Trigger, 'safety/reset', self._srv_reset)
        self.create_service(SetBool, 'safety/set_pilot', self._srv_set_pilot)

        # 7. Timers
        self.create_timer(0.2, self._safety_tick)
        self.create_timer(1.0, self._publish_diagnostics)

        self.get_logger().info('Car Safety Node started – parameter server ready')
        self._log_current_parameters()

    def _declare_parameters(self):
        self.declare_parameter(
            'hands_off.timeout_sec', 2.5,
            ParameterDescriptor(
                description='Seconds of continuous low torque before hands-off is declared',
                floating_point_range=[FloatingPointRange(from_value=0.5, to_value=10.0, step=0.1)]
            )
        )
        self.declare_parameter(
            'hands_off.torque_threshold_nm', 0.6,
            ParameterDescriptor(
                description='Steering torque below this value is considered hands-off',
                floating_point_range=[FloatingPointRange(from_value=0.1, to_value=5.0, step=0.1)]
            )
        )
        self.declare_parameter(
            'health.hr_critical_high', 160,
            ParameterDescriptor(
                description='Heart-rate upper critical limit (bpm)',
                integer_range=[IntegerRange(from_value=100, to_value=220, step=1)]
            )
        )
        self.declare_parameter(
            'health.hr_critical_low', 40,
            ParameterDescriptor(
                description='Heart-rate lower critical limit (bpm)',
                integer_range=[IntegerRange(from_value=20, to_value=60, step=1)]
            )
        )
        self.declare_parameter(
            'health.spo2_critical', 90.0,
            ParameterDescriptor(
                description='Blood-oxygen critical threshold (%)',
                floating_point_range=[FloatingPointRange(from_value=70.0, to_value=95.0, step=0.5)]
            )
        )
        self.declare_parameter(
            'health.breathing_critical', 8,
            ParameterDescriptor(
                description='Breathing rate critical threshold (breaths/min)',
                integer_range=[IntegerRange(from_value=3, to_value=12, step=1)]
            )
        )
        self.declare_parameter(
            'health.bp_sys_critical', 180,
            ParameterDescriptor(
                description='Systolic blood-pressure critical limit',
                integer_range=[IntegerRange(from_value=140, to_value=220, step=1)]
            )
        )
        self.declare_parameter(
            'health.fatigue_critical', 0.85,
            ParameterDescriptor(
                description='Fatigue score (0-1) that triggers critical state',
                floating_point_range=[FloatingPointRange(from_value=0.5, to_value=1.0, step=0.05)]
            )
        )
        self.declare_parameter(
            'long_range.lookahead_m', 160.0,
            ParameterDescriptor(
                description='Maximum distance to consider obstacles (metres)',
                floating_point_range=[FloatingPointRange(from_value=50.0, to_value=300.0, step=5.0)]
            )
        )
        self.declare_parameter(
            'long_range.min_ttc_sec', 3.8,
            ParameterDescriptor(
                description='Time-to-collision threshold that triggers intervention (seconds)',
                floating_point_range=[FloatingPointRange(from_value=1.5, to_value=8.0, step=0.1)]
            )
        )
        self.declare_parameter(
            'vehicle.max_decel_mps2', 6.0,
            ParameterDescriptor(
                description='Maximum deceleration used for emergency pull-over',
                floating_point_range=[FloatingPointRange(from_value=2.0, to_value=10.0, step=0.5)]
            )
        )
        self.declare_parameter(
            'emergency.primary_number', '911',
            ParameterDescriptor(description='Primary emergency telephone number')
        )
        self.declare_parameter(
            'emergency.backup_number', '112',
            ParameterDescriptor(description='Backup emergency telephone number')
        )
        self.declare_parameter(
            'emergency.max_call_retries', 3,
            ParameterDescriptor(
                description='How many times to retry the primary emergency number',
                integer_range=[IntegerRange(from_value=1, to_value=5, step=1)]
            )
        )
        self.declare_parameter('features.hands_off_enabled', True)
        self.declare_parameter('features.health_monitor_enabled', True)
        self.declare_parameter('features.long_range_enabled', True)
        self.declare_parameter('features.auto_hospital_routing', True)

    def _load_parameters(self):
        self.p_hands_timeout = self.get_parameter('hands_off.timeout_sec').value
        self.p_torque_th = self.get_parameter('hands_off.torque_threshold_nm').value
        self.p_hr_high = self.get_parameter('health.hr_critical_high').value
        self.p_hr_low = self.get_parameter('health.hr_critical_low').value
        self.p_spo2 = self.get_parameter('health.spo2_critical').value
        self.p_breath = self.get_parameter('health.breathing_critical').value
        self.p_bp_sys = self.get_parameter('health.bp_sys_critical').value
        self.p_fatigue = self.get_parameter('health.fatigue_critical').value
        self.p_lookahead = self.get_parameter('long_range.lookahead_m').value
        self.p_min_ttc = self.get_parameter('long_range.min_ttc_sec').value
        self.p_max_decel = self.get_parameter('vehicle.max_decel_mps2').value
        self.p_primary_num = self.get_parameter('emergency.primary_number').value
        self.p_backup_num = self.get_parameter('emergency.backup_number').value
        self.p_max_retries = self.get_parameter('emergency.max_call_retries').value
        self.f_hands = self.get_parameter('features.hands_off_enabled').value
        self.f_health = self.get_parameter('features.health_monitor_enabled').value
        self.f_long = self.get_parameter('features.long_range_enabled').value
        self.f_hospital = self.get_parameter('features.auto_hospital_routing').value

    def _on_parameters_changed(self, params: List[Parameter]) -> SetParametersResult:
        for p in params:
            name = p.name
            value = p.value
            if name == 'hands_off.timeout_sec' and (value < 0.5 or value > 10.0):
                return SetParametersResult(successful=False,
                                           reason='hands_off.timeout_sec must be 0.5–10.0')
            if name == 'health.hr_critical_high' and value <= self.p_hr_low:
                return SetParametersResult(successful=False,
                                           reason='hr_critical_high must be > hr_critical_low')
            if name == 'long_range.min_ttc_sec' and value <= 0.5:
                return SetParametersResult(successful=False,
                                           reason='min_ttc_sec too small – unsafe')
        self._load_parameters()
        self.get_logger().info(f'Parameters updated: {[p.name for p in params]}')
        self._publish_event(f'Parameters changed: {[p.name for p in params]}')
        return SetParametersResult(successful=True)

    def _log_current_parameters(self):
        self.get_logger().info('=== Current safety parameters ===')
        self.get_logger().info(f'  hands_off.timeout_sec        = {self.p_hands_timeout}')
        self.get_logger().info(f'  hands_off.torque_threshold   = {self.p_torque_th}')
        self.get_logger().info(f'  health.hr_critical_high      = {self.p_hr_high}')
        self.get_logger().info(f'  health.spo2_critical         = {self.p_spo2}')
        self.get_logger().info(f'  long_range.lookahead_m       = {self.p_lookahead}')
        self.get_logger().info(f'  long_range.min_ttc_sec       = {self.p_min_ttc}')
        self.get_logger().info(f'  features.hands_off_enabled   = {self.f_hands}')
        self.get_logger().info('=================================')

    def _cb_steering(self, msg: Float32):
        self.steering_torque_nm = msg.data

    def _cb_speed(self, msg: Float32):
        self.current_speed_kmh = msg.data

    def _cb_gps(self, msg: NavSatFix):
        self.position = (msg.latitude, msg.longitude)

    def _cb_health(self, msg: String):
        try:
            parts = dict(item.split('=') for item in msg.data.split(',') if '=' in item)
            self.health['heart_rate'] = int(parts.get('hr', self.health['heart_rate']))
            self.health['spo2'] = float(parts.get('spo2', self.health['spo2']))
            self.health['breathing_rate'] = int(parts.get('breath', self.health['breathing_rate']))
            if 'bp' in parts:
                sys, dia = parts['bp'].split('/')
                self.health['bp_sys'] = int(sys)
                self.health['bp_dia'] = int(dia)
            self.health['fatigue'] = float(parts.get('fatigue', self.health['fatigue']))
            alerts = parts.get('alerts', '')
            self.health['alerts'] = [a.strip() for a in alerts.split(';') if a.strip() and a != 'none']
            self.health['status'] = self._evaluate_health()
        except Exception as e:
            self.get_logger().warn(f'Failed to parse health data: {e}')

    def _cb_obstacles(self, msg: String):
        self.last_obstacles.clear()
        try:
            for item in msg.data.split(';'):
                if not item.strip():
                    continue
                d, rs, c, t = item.split(',')
                self.last_obstacles.append(
                    Obstacle(float(d), float(rs), float(c), t.strip())
                )
        except Exception as e:
            self.get_logger().warn(f'Failed to parse obstacles: {e}')

    def _evaluate_health(self) -> HealthStatus:
        h = self.health
        if (h['heart_rate'] >= self.p_hr_high or h['heart_rate'] <= self.p_hr_low or
            h['spo2'] < self.p_spo2 or h['breathing_rate'] < self.p_breath or
            h['bp_sys'] >= self.p_bp_sys or h['fatigue'] >= self.p_fatigue or
            any('critical' in a.lower() or 'arrest' in a.lower() for a in h['alerts'])):
            return HealthStatus.CRITICAL
        if (h['heart_rate'] > 120 or h['spo2'] < 94 or h['breathing_rate'] < 12 or
            h['fatigue'] > 0.6):
            return HealthStatus.WARNING
        return HealthStatus.NORMAL

    def _safety_tick(self):
        if self.f_hands:
            self._check_hands_off()
        if self.f_health:
            self._check_health()
        if self.f_long:
            self._check_long_range()

        mode_msg = String()
        mode_msg.data = self.drive_mode.name
        self.pub_mode.publish(mode_msg)

        pilot_msg = Bool()
        pilot_msg.data = self.pilot_active
        self.pub_pilot.publish(pilot_msg)

        hazard_msg = Bool()
        hazard_msg.data = self.hazard_lights
        self.pub_hazard.publish(hazard_msg)

    def _check_hands_off(self):
        if self.steering_torque_nm < self.p_torque_th:
            if self.hands_off_start is None:
                self.hands_off_start = time.time()
            elif time.time() - self.hands_off_start >= self.p_hands_timeout:
                self._trigger_hands_off()
                self.hands_off_start = None
        else:
            self.hands_off_start = None

    def _check_health(self):
        if self.health['status'] == HealthStatus.CRITICAL:
            self._trigger_medical()

    def _check_long_range(self):
        for obs in self.last_obstacles:
            if obs.distance_m > self.p_lookahead or obs.confidence < 0.5:
                continue
            rel = self.current_speed_kmh - obs.relative_speed_kmh
            if rel <= 0:
                continue
            ttc = (obs.distance_m / 1000.0) / (rel / 3600.0)
            if ttc < self.p_min_ttc:
                self._trigger_collision(obs, ttc)
                break

    def _activate_pilot(self, reason: str):
        if self.pilot_active and self.drive_mode == DriveMode.FULL_AUTONOMOUS:
            return
        self.pilot_active = True
        self.drive_mode = DriveMode.FULL_AUTONOMOUS
        self.hazard_lights = True
        self.get_logger().error(f'PILOT ACTIVATED – {reason}')
        self._publish_event(f'PILOT_ON: {reason}')

    def _trigger_hands_off(self):
        self._activate_pilot('Hands-off steering wheel')
        self._publish_event('HANDS_OFF detected – initiating pull-over')
        self._do_pullover()
        self._call_emergency('HANDS_OFF')

    def _trigger_medical(self):
        self._activate_pilot('Critical medical condition')
        self._publish_event(
            f'MEDICAL critical – HR={self.health["heart_rate"]} '
            f'SpO2={self.health["spo2"]} Fatigue={self.health["fatigue"]:.2f}'
        )
        if self.f_hospital:
            self._publish_event('Routing toward nearest hospital (simulation)')
        self._call_emergency('MEDICAL')

    def _trigger_collision(self, obs: Obstacle, ttc: float):
        self._activate_pilot(f'Collision risk TTC={ttc:.1f}s')
        self._publish_event(
            f'COLLISION_RISK: {obs.type} at {obs.distance_m:.0f}m (TTC {ttc:.1f}s)'
        )
        twist = Twist()
        twist.linear.x = -self.p_max_decel
        self.pub_cmd_vel.publish(twist)

    def _do_pullover(self):
        self.get_logger().warn('Executing roadside pull-over')
        self.is_pulled_over = True
        twist = Twist()
        twist.linear.x = 0.0
        self.pub_cmd_vel.publish(twist)
        self._publish_event('PULLOVER complete – vehicle stopped')

    def _call_emergency(self, reason: str):
        msg = String()
        msg.data = (f'EMERGENCY|{reason}|'
                    f'num={self.p_primary_num}|backup={self.p_backup_num}|'
                    f'lat={self.position[0]:.6f}|lon={self.position[1]:.6f}|'
                    f'retries={self.p_max_retries}')
        self.pub_emergency.publish(msg)
        self.get_logger().error(f'Emergency call requested: {msg.data}')

    def _publish_event(self, text: str):
        msg = String()
        msg.data = f'{time.strftime("%H:%M:%S")} | {text}'
        self.pub_event.publish(msg)

    def _publish_diagnostics(self):
        arr = DiagnosticArray()
        arr.header.stamp = self.get_clock().now().to_msg()

        status = DiagnosticStatus()
        status.name = 'car_safety_system'
        status.hardware_id = 'safety_ecu'
        status.level = DiagnosticStatus.OK
        status.message = 'Running'

        if self.pilot_active:
            status.level = DiagnosticStatus.WARN
            status.message = 'Pilot active'
        if self.health['status'] == HealthStatus.CRITICAL:
            status.level = DiagnosticStatus.ERROR
            status.message = 'Critical health condition'

        status.values = [
            KeyValue(key='drive_mode', value=self.drive_mode.name),
            KeyValue(key='pilot_active', value=str(self.pilot_active)),
            KeyValue(key='speed_kmh', value=f'{self.current_speed_kmh:.1f}'),
            KeyValue(key='steering_torque', value=f'{self.steering_torque_nm:.2f}'),
            KeyValue(key='health_status', value=self.health['status'].name),
            KeyValue(key='heart_rate', value=str(self.health['heart_rate'])),
            KeyValue(key='spo2', value=f'{self.health["spo2"]:.1f}'),
            KeyValue(key='hands_off_timeout', value=str(self.p_hands_timeout)),
            KeyValue(key='min_ttc', value=str(self.p_min_ttc)),
        ]
        arr.status.append(status)
        self.pub_diagnostics.publish(arr)

    def _srv_force_pullover(self, request, response):
        self._activate_pilot('Manual force pullover service')
        self._do_pullover()
        response.success = True
        response.message = 'Pull-over commanded'
        return response

    def _srv_reset(self, request, response):
        self.pilot_active = False
        self.drive_mode = DriveMode.MANUAL
        self.is_pulled_over = False
        self.hazard_lights = False
        self.hands_off_start = None
        self.health['status'] = HealthStatus.NORMAL
        self._publish_event('System reset via service')
        response.success = True
        response.message = 'Safety system reset to manual'
        return response

    def _srv_set_pilot(self, request, response):
        if request.data:
            self._activate_pilot('Service request')
        else:
            if self.health['status'] == HealthStatus.CRITICAL:
                response.success = False
                response.message = 'Cannot deactivate pilot while health is CRITICAL'
                return response
            self.pilot_active = False
            self.drive_mode = DriveMode.MANUAL
            self.hazard_lights = False
            self._publish_event('Pilot deactivated via service')
        response.success = True
        response.message = f'Pilot set to {request.data}'
        return response


def main(args=None):
    rclpy.init(args=args)
    node = CarSafetyNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
