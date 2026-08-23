#!/usr/bin/env python3
"""
Car Safety System – Animated Terminal Preview
=============================================
A self-contained cinematic demo that shows how the ROS 2 safety
system reacts to hands-off, medical emergency, and long-range threats.
No ROS 2 installation required.
"""

import os
import sys
import time
import math
from datetime import datetime

# ANSI colours
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
MAGENTA= "\033[95m"
CYAN   = "\033[96m"
WHITE  = "\033[97m"
BG_RED = "\033[41m"
BG_YEL = "\033[43m"
BG_GRN = "\033[42m"

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def sleep(t=0.8):
    time.sleep(t)

def header(title):
    print(f"\n{BOLD}{CYAN}{'\u2550'*64}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'\u2550'*64}{RESET}\n")

def event(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    colours = {
        "INFO": BLUE,
        "WARN": YELLOW,
        "CRIT": RED,
        "OK":   GREEN,
        "PILOT": MAGENTA,
    }
    c = colours.get(level, WHITE)
    print(f"  {DIM}{ts}{RESET}  {c}{BOLD}[{level:5}]{RESET}  {msg}")

def car_ascii(mode="MANUAL", speed=90, pilot=False, hazard=False, pulled=False):
    mode_col = GREEN if mode == "MANUAL" else (YELLOW if mode == "ASSISTED" else MAGENTA)
    pilot_str = f"{MAGENTA}PILOT ON{RESET}" if pilot else f"{DIM}pilot off{RESET}"
    hazard_str = f"{RED}\u25c6 HAZARD{RESET}" if hazard else "        "
    status = f"{RED}PULLED OVER{RESET}" if pulled else f"{speed:5.1f} km/h"

    print(f"""
    {BOLD}\u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510{RESET}
    \u2502  {mode_col}{mode:^16}{RESET}   {pilot_str}   {hazard_str} \u2502
    \u2502                                             \u2502
    \u2502           \U0001f697  \u2550\u2550\u2550\u2550\u2550\u2550\u2557                       \u2502
    \u2502              \u2551      \u2551  Speed: {status:<12} \u2502
    \u2502              \u255a\u2550\u2550\u2550\u2550\u2550\u2550\u255d                       \u2502
    \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518
    """)

def dashboard(hr=72, spo2=98, breath=16, fatigue=0.1, status="NORMAL",
              torque=4.5, ttc=None, obstacles=0):
    st_col = GREEN if status == "NORMAL" else (YELLOW if status == "WARNING" else RED)
    print(f"""  {BOLD}Health Monitor (Watch){RESET}
  \u251c Heart Rate   : {hr:3d} bpm
  \u251c SpO\u2082         : {spo2:5.1f} %
  \u251c Breathing    : {breath:2d} /min
  \u251c Fatigue      : {fatigue:.2f}
  \u2514 Status       : {st_col}{BOLD}{status}{RESET}

  {BOLD}Vehicle Sensors{RESET}
  \u251c Steering torque : {torque:4.1f} Nm
  \u251c Obstacles tracked: {obstacles}
  \u2514 Time-to-collision: {ttc if ttc else "\u2014"}
""")

def progress_bar(label, seconds=2.0, width=30):
    print(f"  {label}")
    for i in range(width + 1):
        filled = "\u2588" * i
        empty  = "\u2591" * (width - i)
        pct = int(i / width * 100)
        sys.stdout.write(f"\r  [{GREEN}{filled}{RESET}{empty}] {pct:3d}%")
        sys.stdout.flush()
        time.sleep(seconds / width)
    print()

def animate_pullover():
    print(f"\n  {YELLOW}Executing controlled roadside pull-over\u2026{RESET}")
    for spd in [90, 75, 55, 35, 15, 0]:
        car_ascii(mode="FULL_AUTONOMOUS", speed=spd, pilot=True, hazard=True)
        sleep(0.45)
        clear()
        header("SCENARIO \u2013 Hands Off / Pull-over")
    car_ascii(mode="FULL_AUTONOMOUS", speed=0, pilot=True, hazard=True, pulled=True)
    event("Vehicle stopped safely on shoulder", "OK")

def animate_emergency_call():
    print(f"\n  {RED}{BOLD}EMERGENCY CALL SEQUENCE{RESET}")
    for attempt in range(1, 4):
        event(f"Calling 911  (attempt {attempt}/3) \u2026", "CRIT")
        progress_bar("  Dialling", 1.1)
        if attempt < 3:
            event("No answer", "WARN")
            sleep(0.3)
        else:
            event("Connected \u2013 sharing live GPS location", "OK")
            event("Live location stream started \u2192 37.77490, -122.41940", "INFO")
    event("Backup line 112 also notified", "INFO")

def run_demo():
    clear()
    print(f"""
{BOLD}{CYAN}
  \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557
  \u2551     AUTOMATED CAR SAFETY SYSTEM \u2013 LIVE PREVIEW           \u2551
  \u2551     (ROS 2 parameter-server version \u2013 simulation)        \u2551
  \u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d
{RESET}
  This animation shows three critical scenarios the system handles.
""")
    sleep(2.0)

    # SCENARIO 1
    clear()
    header("SCENARIO 1 / 3  \u2013  Normal driving")
    car_ascii(mode="MANUAL", speed=92, pilot=False)
    dashboard(hr=74, spo2=98.2, breath=15, fatigue=0.12, status="NORMAL", torque=4.8)
    event("All systems nominal", "OK")
    event("Parameter server loaded (hands_off.timeout=2.5s, min_ttc=3.8s)", "INFO")
    sleep(2.5)

    # SCENARIO 2
    clear()
    header("SCENARIO 2 / 3  \u2013  Driver lifts hands from wheel")
    car_ascii(mode="MANUAL", speed=88, pilot=False)
    dashboard(torque=0.2, status="NORMAL")
    event("Steering torque dropped below 0.6 Nm", "WARN")
    sleep(1.0)

    for remaining in [2.0, 1.5, 1.0, 0.5, 0.0]:
        clear()
        header("SCENARIO 2 / 3  \u2013  Hands-off timer")
        car_ascii(mode="MANUAL", speed=87, pilot=False)
        dashboard(torque=0.15)
        event(f"Hands-off timer: {remaining:.1f}s remaining", "WARN")
        sleep(0.55)

    clear()
    header("SCENARIO 2 / 3  \u2013  Hands-off CONFIRMED")
    event("HANDS-OFF detected \u2013 activating background pilot", "CRIT")
    sleep(0.8)
    event("Pilot engaged \u2192 mode switched to FULL_AUTONOMOUS", "PILOT")
    sleep(0.6)

    animate_pullover()
    sleep(1.0)
    animate_emergency_call()
    sleep(2.5)

    # SCENARIO 3
    clear()
    header("SCENARIO 3 / 3  \u2013  Critical medical event (smartwatch)")
    car_ascii(mode="MANUAL", speed=95, pilot=False)
    dashboard(hr=72, spo2=97, breath=14, fatigue=0.2, status="NORMAL", torque=4.5)
    event("Driver appears healthy \u2013 monitoring continues", "OK")
    sleep(1.8)

    clear()
    header("SCENARIO 3 / 3  \u2013  Sudden critical readings")
    car_ascii(mode="MANUAL", speed=94, pilot=False)
    dashboard(hr=28, spo2=79, breath=5, fatigue=0.94, status="CRITICAL", torque=3.1)
    event("CRITICAL health status from watch", "CRIT")
    event("HR=28  SpO\u2082=79%  Breathing=5  Fatigue=0.94", "CRIT")
    event("Custom alert: possible cardiac arrest", "CRIT")
    sleep(1.5)

    event("Background pilot ACTIVATED (even though mode was MANUAL)", "PILOT")
    sleep(0.7)
    event("Hazard lights ON", "WARN")
    event("Computing route to nearest hospital\u2026", "INFO")
    progress_bar("  Routing", 1.4)
    event("Nearest hospital: SF General (2.4 km) \u2013 ETA \u2248 4 min", "OK")
    event("Hospital notified of condition + live location", "INFO")
    event("Emergency contacts + 911 notified", "CRIT")
    sleep(1.2)

    clear()
    header("SCENARIO 3 / 3  \u2013  En-route to hospital")
    car_ascii(mode="FULL_AUTONOMOUS", speed=70, pilot=True, hazard=True)
    dashboard(hr=31, spo2=81, breath=6, fatigue=0.95, status="CRITICAL", torque=0.0)
    event("Pilot has full control \u2013 driver override blocked while CRITICAL", "PILOT")
    event("Live location streaming every 2 s", "INFO")
    sleep(2.5)

    # BONUS
    clear()
    header("BONUS  \u2013  Long-range obstacle detection")
    car_ascii(mode="MANUAL", speed=105, pilot=False)
    dashboard(torque=4.2, ttc="2.9 s", obstacles=1)
    event("Stopped truck detected at 95 m", "WARN")
    event("Time-to-collision = 2.9 s  (< min_ttc 3.8 s)", "CRIT")
    sleep(1.0)
    event("Pilot activated \u2013 automatic braking requested", "PILOT")
    progress_bar("  Decelerating", 1.6)
    car_ascii(mode="FULL_AUTONOMOUS", speed=40, pilot=True, hazard=True)
    event("Collision avoided \u2013 speed reduced", "OK")
    sleep(2.0)

    clear()
    print(f"""
{BOLD}{GREEN}
  \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557
  \u2551                    DEMO COMPLETE                         \u2551
  \u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d
{RESET}
  The system demonstrated:

  {GREEN}\u2713{RESET}  Hands-off detection \u2192 pull-over + emergency call + live location
  {GREEN}\u2713{RESET}  Smartwatch critical event \u2192 pilot takeover + hospital routing
  {GREEN}\u2713{RESET}  Background pilot that can override manual mode
  {GREEN}\u2713{RESET}  Long-range obstacle detection & automatic braking
  {GREEN}\u2713{RESET}  All thresholds controlled by the ROS 2 parameter server

  {DIM}In the real ROS 2 package these events appear on topics
  /safety/events, /safety/emergency, /diagnostics, etc.
  Parameters can be changed live with:{RESET}

      ros2 param set /car_safety_node hands_off.timeout_sec 1.8

  {CYAN}Thank you for watching the preview.{RESET}
""")

if __name__ == "__main__":
    try:
        run_demo()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Demo interrupted.{RESET}")
