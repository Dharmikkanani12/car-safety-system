# Car Safety System

ROS 2 + pure-Python automated car safety system featuring:

- **Hands-off detection** → automatic roadside pull-over + emergency call + live location sharing
- **Smartwatch / health monitoring** → critical medical event detection → hospital routing + notifications
- **Background pilot** that can take control even in pure manual mode
- **Long-range obstacle / collision avoidance**
- Full **ROS 2 parameter server** support (all thresholds configurable at runtime)

## Repository contents

| File / Folder | Description |
|---------------|-------------|
| **`car_safety_core.py`** | **Full pure-Python core** (main logic from the original design) |
| **`CIRCUIT_AND_ARCHITECTURE.md`** | **Circuit-style block diagram + Mermaid architecture** |
| `car_safety_demo_animation.py` | Terminal cinematic demo |
| `car_safety_preview.html` | Interactive browser dashboard |
| `car_safety_system/` | ROS 2 package (parameter server, node, launch, config) |

## Quick start (no ROS required)

```bash
# Full core system with 4 scenarios
python3 car_safety_core.py

# Terminal animation
python3 car_safety_demo_animation.py

# Open HTML dashboard in a browser
# (or: python3 -m http.server)
```

## Circuit & architecture

See **[CIRCUIT_AND_ARCHITECTURE.md](CIRCUIT_AND_ARCHITECTURE.md)** for:

- Hardware-style block diagram (sensors → Safety ECU → actuators / eCall)
- Signal-flow circuit sketch
- Mermaid software architecture (renders on GitHub)
- Mapping of each block to code classes

## ROS 2 package

```bash
cd ~/ros2_ws/src
# clone or copy car_safety_system here
cd ~/ros2_ws
colcon build --packages-select car_safety_system
source install/setup.bash
ros2 launch car_safety_system safety.launch.py
```

Parameter examples:

```bash
ros2 param list /car_safety_node
ros2 param set /car_safety_node hands_off.timeout_sec 1.8
ros2 param set /car_safety_node features.long_range_enabled false
```

## License

Apache-2.0
