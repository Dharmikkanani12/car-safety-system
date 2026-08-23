# car_safety_system – ROS 2 Package

ROS 2 node that implements the automated-car safety features:

- Hands-off steering detection → pull-over + emergency call
- Smartwatch / health-monitor integration → hospital routing on critical events
- Background pilot activation (even from pure manual mode)
- Long-range obstacle / collision-risk detection

**All thresholds and feature flags are exposed through the ROS 2 parameter server** and can be changed at runtime.

## Package layout

```
car_safety_system/
├── car_safety_system/
│   ├── __init__.py
│   ├── safety_node.py          # Main safety node + parameter server
│   └── parameter_demo.py       # Example client that talks to the parameter server
├── config/
│   └── safety_params.yaml      # Default parameter values
├── launch/
│   └── safety.launch.py
├── package.xml
├── setup.py
└── setup.cfg
```

## Build & run (ROS 2 Humble / Iron / Jazzy)

```bash
# Inside your ROS 2 workspace
cd ~/ros2_ws/src
# copy or symlink this package here
cd ~/ros2_ws
rosdep install --from-paths src -y --ignore-src
colcon build --packages-select car_safety_system
source install/setup.bash

# Launch with default parameters
ros2 launch car_safety_system safety.launch.py

# Or override the YAML
ros2 launch car_safety_system safety.launch.py params_file:=/path/to/my_params.yaml
```

## ROS 2 Parameter Server usage

The node automatically advertises the standard parameter services:

| Service | Purpose |
|---------|---------|
| `/car_safety_node/get_parameters` | Read parameter values |
| `/car_safety_node/set_parameters` | Change parameters at runtime |
| `/car_safety_node/list_parameters` | List all parameter names |
| `/car_safety_node/describe_parameters` | Get type, range, description |
| `/car_safety_node/get_parameter_types` | Get types only |

### Command-line examples

```bash
# List everything
ros2 param list /car_safety_node

# Read one value
ros2 param get /car_safety_node hands_off.timeout_sec

# Change a value (triggers the validation callback)
ros2 param set /car_safety_node hands_off.timeout_sec 1.8
ros2 param set /car_safety_node health.hr_critical_high 150
ros2 param set /car_safety_node features.long_range_enabled false

# Dump all current values
ros2 param dump /car_safety_node
```

### From another node

See `parameter_demo.py` – it shows how to call the Get/Set/List services programmatically.

```bash
# In another terminal (while safety_node is running)
ros2 run car_safety_system parameter_demo
```

## Topics

| Topic | Type | Direction | Description |
|-------|------|-----------|-------------|
| `vehicle/steering_torque` | `std_msgs/Float32` | In | Steering wheel torque (Nm) |
| `vehicle/speed` | `std_msgs/Float32` | In | Current speed (km/h) |
| `vehicle/gps` | `sensor_msgs/NavSatFix` | In | GPS position |
| `health/watch_data` | `std_msgs/String` | In | Health data from watch |
| `perception/obstacles` | `std_msgs/String` | In | Obstacle list |
| `safety/drive_mode` | `std_msgs/String` | Out | Current mode |
| `safety/pilot_active` | `std_msgs/Bool` | Out | Pilot engaged? |
| `safety/hazard_lights` | `std_msgs/Bool` | Out | Hazard status |
| `safety/cmd_vel` | `geometry_msgs/Twist` | Out | Emergency motion commands |
| `safety/events` | `std_msgs/String` | Out | Human-readable events |
| `safety/emergency` | `std_msgs/String` | Out | Emergency call requests |
| `diagnostics` | `diagnostic_msgs/DiagnosticArray` | Out | Status for rqt / robot monitor |

## Services

| Service | Type | Description |
|---------|------|-------------|
| `safety/force_pullover` | `std_srvs/Trigger` | Force an immediate pull-over |
| `safety/reset` | `std_srvs/Trigger` | Reset to manual mode |
| `safety/set_pilot` | `std_srvs/SetBool` | Enable / disable pilot (blocked if health is CRITICAL) |

## Parameter groups

- `hands_off.*` – torque threshold & timeout
- `health.*` – heart-rate, SpO₂, breathing, blood-pressure, fatigue limits
- `long_range.*` – lookahead distance & time-to-collision threshold
- `vehicle.*` – deceleration limits
- `emergency.*` – phone numbers & retry count
- `features.*` – enable/disable individual safety functions

All numeric parameters have declared min/max ranges that appear in `ros2 param describe` and in rqt.

## Notes

- This is an educational / prototyping package. Real vehicle deployment requires ISO 26262 processes, certified hardware, and proper motion-planning integration.
- Custom message definitions can be added later if you prefer strongly-typed health / obstacle messages instead of the simple String formats used here.
