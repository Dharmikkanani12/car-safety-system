#!/usr/bin/env python3
"""
Automated Car Safety System – Full Core Implementation
======================================================
This is the complete pure-Python version of the safety system
(before the ROS 2 wrapper). It includes:

1. Hands-off steering detection → pull-over + emergency call + live location
2. Smartwatch / health monitoring → critical event → hospital routing
3. Background pilot activation (even in pure manual mode)
4. Long-range obstacle / accident-prevention detection
5. Continuous monitoring thread, event logging, configurable thresholds,
   simulated GPS/hospital lookup, fail-safes, multi-threat handling

Run:
    python3 car_safety_core.py          # automated scenarios
    python3 car_safety_core.py interactive
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Tuple
import time
import random
import threading
import math
from datetime import datetime
from collections import deque


@dataclass
class SafetyConfig:
    hands_off_timeout_sec: float = 2.5
    steering_torque_threshold_nm: float = 0.6
    hr_critical_high: int = 160
    hr_critical_low: int = 40
    spo2_critical: float = 90.0
    breathing_critical: int = 8
    bp_systolic_critical: int = 180
    fatigue_score_critical: float = 0.85
    lookahead_distance_m: float = 160.0
    min_ttc_sec: float = 3.8
    max_decel_mps2: float = 6.0
    pull_over_target_speed: float = 0.0
    primary_emergency_number: str = "911"
    backup_emergency_number: str = "112"
    max_call_retries: int = 3
    location_update_interval_sec: float = 2.0


class DriveMode(Enum):
    MANUAL = auto()
    ASSISTED = auto()
    FULL_AUTONOMOUS = auto()


class HealthStatus(Enum):
    NORMAL = auto()
    WARNING = auto()
    CRITICAL = auto()


class EmergencyType(Enum):
    HANDS_OFF = "Hands off steering wheel"
    MEDICAL = "Medical emergency"
    COLLISION_RISK = "Imminent collision risk"
    SYSTEM_FAULT = "Critical system fault"


class EventSeverity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class GeoPoint:
    lat: float
    lon: float

    def distance_to(self, other: GeoPoint) -> float:
        R = 6371000
        phi1, phi2 = math.radians(self.lat), math.radians(other.lat)
        dphi = math.radians(other.lat - self.lat)
        dlambda = math.radians(other.lon - self.lon)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))


@dataclass
class VehicleState:
    speed_kmh: float = 0.0
    steering_torque_nm: float = 5.0
    mode: DriveMode = DriveMode.MANUAL
    position: GeoPoint = field(default_factory=lambda: GeoPoint(37.7749, -122.4194))
    heading_deg: float = 90.0
    is_pulled_over: bool = False
    pilot_active: bool = False
    hazard_lights: bool = False
    last_update: datetime = field(default_factory=datetime.now)


@dataclass
class HealthData:
    heart_rate: int = 72
    spo2: float = 98.0
    breathing_rate: int = 16
    blood_pressure_sys: int = 120
    blood_pressure_dia: int = 80
    fatigue_score: float = 0.1
    custom_alerts: List[str] = field(default_factory=list)
    status: HealthStatus = HealthStatus.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Obstacle:
    distance_m: float
    relative_speed_kmh: float
    lateral_offset_m: float = 0.0
    type: str = "unknown"
    confidence: float = 0.9


@dataclass
class SafetyEvent:
    timestamp: datetime
    severity: EventSeverity
    event_type: str
    message: str
    data: Dict = field(default_factory=dict)


class EventLogger:
    def __init__(self, max_events: int = 200):
        self.events: deque[SafetyEvent] = deque(maxlen=max_events)
        self._lock = threading.Lock()

    def log(self, severity: EventSeverity, event_type: str, message: str, **data):
        evt = SafetyEvent(timestamp=datetime.now(), severity=severity,
                          event_type=event_type, message=message, data=data)
        with self._lock:
            self.events.append(evt)
        prefix = {EventSeverity.INFO: "[INFO ]", EventSeverity.WARNING: "[WARN ]",
                  EventSeverity.CRITICAL: "[CRIT ]"}[severity]
        print(f"{prefix} {evt.timestamp.strftime('%H:%M:%S')} | {event_type}: {message}")

    def recent(self, n: int = 10) -> List[SafetyEvent]:
        with self._lock:
            return list(self.events)[-n:]


class HospitalFinder:
    HOSPITALS = [
        ("SF General Hospital", GeoPoint(37.7558, -122.4051)),
        ("UCSF Medical Center", GeoPoint(37.7631, -122.4579)),
        ("Kaiser Permanente SF", GeoPoint(37.7833, -122.4333)),
        ("St. Mary's Medical Center", GeoPoint(37.7900, -122.4400)),
    ]

    def nearest(self, pos: GeoPoint) -> Tuple[str, GeoPoint, float]:
        best = min(self.HOSPITALS, key=lambda h: pos.distance_to(h[1]))
        name, loc = best
        return name, loc, pos.distance_to(loc)


class HandsOffMonitor:
    def __init__(self, cfg: SafetyConfig):
        self.cfg = cfg
        self._start: Optional[float] = None

    def update(self, torque: float) -> bool:
        if torque < self.cfg.steering_torque_threshold_nm:
            if self._start is None:
                self._start = time.time()
            elif time.time() - self._start >= self.cfg.hands_off_timeout_sec:
                return True
        else:
            self._start = None
        return False

    def reset(self):
        self._start = None


class HealthMonitor:
    def __init__(self, cfg: SafetyConfig):
        self.cfg = cfg

    def evaluate(self, data: HealthData) -> HealthStatus:
        critical = (
            data.heart_rate >= self.cfg.hr_critical_high or
            data.heart_rate <= self.cfg.hr_critical_low or
            data.spo2 < self.cfg.spo2_critical or
            data.breathing_rate < self.cfg.breathing_critical or
            data.blood_pressure_sys >= self.cfg.bp_systolic_critical or
            data.fatigue_score >= self.cfg.fatigue_score_critical or
            any("critical" in a.lower() or "arrest" in a.lower() for a in data.custom_alerts)
        )
        if critical:
            return HealthStatus.CRITICAL
        warning = (data.heart_rate > 120 or data.heart_rate < 50 or
                   data.spo2 < 94 or data.breathing_rate < 12 or data.fatigue_score > 0.6)
        return HealthStatus.WARNING if warning else HealthStatus.NORMAL


class LongRangeSafety:
    def __init__(self, cfg: SafetyConfig):
        self.cfg = cfg

    def assess(self, obstacles: List[Obstacle], ego_speed: float) -> Optional[Obstacle]:
        for obs in obstacles:
            if obs.distance_m > self.cfg.lookahead_distance_m or obs.confidence < 0.5:
                continue
            rel_speed = ego_speed - obs.relative_speed_kmh
            if rel_speed <= 0:
                continue
            ttc = (obs.distance_m / 1000.0) / (rel_speed / 3600.0)
            if ttc < self.cfg.min_ttc_sec:
                return obs
        return None


class EmergencyHandler:
    def __init__(self, cfg: SafetyConfig, logger: EventLogger):
        self.cfg = cfg
        self.logger = logger
        self.contacts = ["+1-555-0123 (Primary Contact)", "+1-555-0199 (Secondary)"]
        self._location_stream_active = False
        self._stream_thread: Optional[threading.Thread] = None

    def call_emergency(self, reason: EmergencyType, location: GeoPoint) -> bool:
        self.logger.log(EventSeverity.CRITICAL, "EMERGENCY_CALL",
                        f"Calling {self.cfg.primary_emergency_number} – {reason.value}",
                        lat=location.lat, lon=location.lon)
        for attempt in range(1, self.cfg.max_call_retries + 1):
            self.logger.log(EventSeverity.INFO, "CALL_ATTEMPT",
                            f"Attempt {attempt}/{self.cfg.max_call_retries}")
            time.sleep(0.6)
            if random.random() > 0.25:
                self.logger.log(EventSeverity.INFO, "CALL_CONNECTED",
                                "Emergency services connected. Sharing live telemetry.")
                self.start_live_location_stream(location)
                return True
        self.logger.log(EventSeverity.WARNING, "CALL_FALLBACK",
                        f"No answer on primary. Dialing backup {self.cfg.backup_emergency_number}")
        self.start_live_location_stream(location)
        return True

    def notify_hospital_and_contacts(self, hospital_name: str, condition: str,
                                     location: GeoPoint, eta_min: float):
        self.logger.log(EventSeverity.CRITICAL, "HOSPITAL_NOTIFY",
                        f"{hospital_name} notified | ETA ≈ {eta_min:.0f} min | {condition}")
        for c in self.contacts:
            self.logger.log(EventSeverity.INFO, "CONTACT_NOTIFY", f"Notified {c}: {condition}")

    def start_live_location_stream(self, initial: GeoPoint):
        if self._location_stream_active:
            return
        self._location_stream_active = True
        def _stream():
            pos = initial
            while self._location_stream_active:
                pos = GeoPoint(pos.lat + random.uniform(-0.0001, 0.0001),
                               pos.lon + random.uniform(-0.0001, 0.0001))
                self.logger.log(EventSeverity.INFO, "LIVE_LOCATION",
                                f"Streaming → {pos.lat:.6f}, {pos.lon:.6f}")
                time.sleep(self.cfg.location_update_interval_sec)
        self._stream_thread = threading.Thread(target=_stream, daemon=True)
        self._stream_thread.start()

    def stop_live_location_stream(self):
        self._location_stream_active = False


class PilotController:
    def __init__(self, cfg: SafetyConfig, logger: EventLogger):
        self.cfg = cfg
        self.logger = logger

    def activate(self, state: VehicleState, reason: str):
        if state.pilot_active and state.mode == DriveMode.FULL_AUTONOMOUS:
            return
        self.logger.log(EventSeverity.CRITICAL, "PILOT_ACTIVATE",
                        f"Background pilot engaged – {reason}")
        state.pilot_active = True
        state.mode = DriveMode.FULL_AUTONOMOUS
        state.hazard_lights = True

    def pull_to_side(self, state: VehicleState):
        self.logger.log(EventSeverity.WARNING, "PULLOVER", "Executing controlled roadside pull-over")
        while state.speed_kmh > self.cfg.pull_over_target_speed:
            state.speed_kmh = max(0.0, state.speed_kmh - self.cfg.max_decel_mps2 * 0.5 * 3.6)
            time.sleep(0.15)
        state.is_pulled_over = True
        state.speed_kmh = 0.0
        self.logger.log(EventSeverity.INFO, "PULLOVER_COMPLETE",
                        "Vehicle stopped safely on shoulder / roadside")

    def route_to_hospital(self, state: VehicleState, hospital: Tuple[str, GeoPoint, float]):
        name, loc, dist_m = hospital
        eta_min = (dist_m / 1000) / 50 * 60
        self.logger.log(EventSeverity.CRITICAL, "HOSPITAL_ROUTE",
                        f"Routing to {name} ({dist_m/1000:.1f} km) | ETA ≈ {eta_min:.0f} min")
        state.hazard_lights = True
        return eta_min


class CarSafetySystem:
    def __init__(self, config: Optional[SafetyConfig] = None):
        self.cfg = config or SafetyConfig()
        self.state = VehicleState()
        self.health = HealthData()
        self.logger = EventLogger()
        self.hands = HandsOffMonitor(self.cfg)
        self.health_mon = HealthMonitor(self.cfg)
        self.long_range = LongRangeSafety(self.cfg)
        self.emergency = EmergencyHandler(self.cfg, self.logger)
        self.pilot = PilotController(self.cfg, self.logger)
        self.hospital_finder = HospitalFinder()
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._last_obstacles: List[Obstacle] = []
        self._lock = threading.Lock()

    def start_monitoring(self, interval_sec: float = 0.25):
        if self._running:
            return
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval_sec,), daemon=True)
        self._monitor_thread.start()
        self.logger.log(EventSeverity.INFO, "SYSTEM", "Continuous safety monitoring started")

    def stop_monitoring(self):
        self._running = False
        self.emergency.stop_live_location_stream()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        self.logger.log(EventSeverity.INFO, "SYSTEM", "Monitoring stopped")

    def update_steering_torque(self, torque_nm: float):
        with self._lock:
            self.state.steering_torque_nm = torque_nm

    def update_health(self, **kwargs):
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self.health, k):
                    setattr(self.health, k, v)
            self.health.timestamp = datetime.now()
            self.health.status = self.health_mon.evaluate(self.health)

    def update_obstacles(self, obstacles: List[Obstacle]):
        with self._lock:
            self._last_obstacles = obstacles

    def set_speed(self, speed_kmh: float):
        with self._lock:
            self.state.speed_kmh = max(0.0, speed_kmh)

    def force_manual_mode(self):
        with self._lock:
            if self.health.status == HealthStatus.CRITICAL or self.state.is_pulled_over:
                self.logger.log(EventSeverity.WARNING, "OVERRIDE_BLOCKED",
                                "Manual override denied – critical condition active")
                self.state.mode = DriveMode.FULL_AUTONOMOUS
            else:
                self.state.mode = DriveMode.MANUAL
                self.state.pilot_active = False
                self.logger.log(EventSeverity.INFO, "MANUAL_MODE", "Driver regained control")

    def _monitor_loop(self, interval: float):
        while self._running:
            try:
                self._tick()
            except Exception as e:
                self.logger.log(EventSeverity.CRITICAL, "SYSTEM_FAULT", f"Monitor loop exception: {e}")
            time.sleep(interval)

    def _tick(self):
        with self._lock:
            state = self.state
            health = self.health
            obstacles = list(self._last_obstacles)
        if self.hands.update(state.steering_torque_nm):
            self._handle_hands_off()
        if health.status == HealthStatus.CRITICAL:
            self._handle_medical()
        threat = self.long_range.assess(obstacles, state.speed_kmh)
        if threat:
            self._handle_collision(threat)
        if state.pilot_active and state.mode != DriveMode.FULL_AUTONOMOUS:
            state.mode = DriveMode.FULL_AUTONOMOUS

    def _handle_hands_off(self):
        self.logger.log(EventSeverity.CRITICAL, "HANDS_OFF", "Prolonged hands-off detected")
        self.pilot.activate(self.state, EmergencyType.HANDS_OFF.value)
        self.pilot.pull_to_side(self.state)
        self.emergency.call_emergency(EmergencyType.HANDS_OFF, self.state.position)
        self.hands.reset()

    def _handle_medical(self):
        self.logger.log(EventSeverity.CRITICAL, "MEDICAL",
                        f"Critical health – HR={self.health.heart_rate} SpO2={self.health.spo2}% "
                        f"BP={self.health.blood_pressure_sys}/{self.health.blood_pressure_dia} "
                        f"Fatigue={self.health.fatigue_score:.2f}")
        self.pilot.activate(self.state, EmergencyType.MEDICAL.value)
        hospital = self.hospital_finder.nearest(self.state.position)
        eta = self.pilot.route_to_hospital(self.state, hospital)
        condition = (f"Possible cardiac/respiratory event | HR {self.health.heart_rate} | "
                     f"SpO2 {self.health.spo2}% | Alerts: {self.health.custom_alerts or 'none'}")
        self.emergency.notify_hospital_and_contacts(hospital[0], condition, self.state.position, eta)
        self.emergency.call_emergency(EmergencyType.MEDICAL, self.state.position)

    def _handle_collision(self, obs: Obstacle):
        self.logger.log(EventSeverity.CRITICAL, "COLLISION_RISK",
                        f"{obs.type} at {obs.distance_m:.0f} m | rel speed {obs.relative_speed_kmh:.0f} km/h | conf {obs.confidence:.2f}")
        self.pilot.activate(self.state, EmergencyType.COLLISION_RISK.value)
        self.logger.log(EventSeverity.WARNING, "AVOIDANCE", "Automatic braking / evasive trajectory requested")


def run_expanded_demo():
    print("=" * 70)
    print("  AUTOMATED CAR SAFETY SYSTEM – FULL CORE DEMO")
    print("=" * 70)
    system = CarSafetySystem()
    system.start_monitoring(interval_sec=0.3)
    system.set_speed(95)
    system.update_steering_torque(4.5)
    system.update_health(heart_rate=74, spo2=98, breathing_rate=15)
    time.sleep(1.5)

    print("\n" + "\u2500" * 60)
    print("SCENARIO 1: Driver lifts both hands from the wheel")
    print("\u2500" * 60)
    system.update_steering_torque(0.1)
    time.sleep(4.0)

    system.state.is_pulled_over = False
    system.state.pilot_active = False
    system.state.mode = DriveMode.MANUAL
    system.state.hazard_lights = False
    system.emergency.stop_live_location_stream()
    system.set_speed(85)
    system.update_steering_torque(5.0)
    time.sleep(1.0)

    print("\n" + "\u2500" * 60)
    print("SCENARIO 2: Critical medical event from smartwatch")
    print("\u2500" * 60)
    system.update_health(heart_rate=32, spo2=81, breathing_rate=5, blood_pressure_sys=70,
                         blood_pressure_dia=40, fatigue_score=0.95,
                         custom_alerts=["possible cardiac arrest", "unresponsive"])
    time.sleep(2.5)

    print("\n" + "\u2500" * 60)
    print("SCENARIO 3: Distant stopped vehicle detected")
    print("\u2500" * 60)
    system.state.pilot_active = False
    system.state.mode = DriveMode.MANUAL
    system.set_speed(100)
    system.update_obstacles([
        Obstacle(distance_m=110, relative_speed_kmh=5, type="stopped truck", confidence=0.93),
        Obstacle(distance_m=45, relative_speed_kmh=80, type="overtaking car", confidence=0.88),
    ])
    time.sleep(2.0)

    print("\n" + "\u2500" * 60)
    print("SCENARIO 4: Driver attempts manual override during critical condition")
    print("\u2500" * 60)
    system.force_manual_mode()
    time.sleep(1.5)
    system.stop_monitoring()

    print("\n" + "=" * 70)
    print("  DEMO COMPLETE – Recent events:")
    print("=" * 70)
    for evt in system.logger.recent(12):
        print(f"  {evt.timestamp.strftime('%H:%M:%S')} [{evt.severity.value}] {evt.event_type}: {evt.message}")


if __name__ == "__main__":
    run_expanded_demo()
