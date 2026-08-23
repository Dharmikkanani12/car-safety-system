# Car Safety System

ROS 2 automated car safety system featuring:

- **Hands-off detection** → automatic roadside pull-over + emergency call + live location sharing
- **Smartwatch / health monitoring** → critical medical event detection → hospital routing + notifications
- **Background pilot** that can take control even in pure manual mode
- **Long-range obstacle / collision avoidance**
- Full **ROS 2 parameter server** support (all thresholds configurable at runtime)

## Quick demos (no ROS 2 required)

```bash
# Terminal animation
python3 car_safety_demo_animation.py

# Open the interactive HTML dashboard in a browser
# (or serve it: python3 -m http.server)
```

Open `car_safety_preview.html` in any browser for the visual dashboard with buttons to trigger each scenario.

## ROS 2 package

See [`car_safety_system/README.md`](car_safety_system/README.md) for build & run instructions.

```bash
cd ~/ros2_ws/src
# clone or copy car_safety_system here
cd ~/ros2_ws
colcon build --packages-select car_safety_system
source install/setup.bash
ros2 launch car_safety_system safety.launch.py
```

## Parameter server examples

```bash
ros2 param list /car_safety_node
ros2 param set /car_safety_node hands_off.timeout_sec 1.8
ros2 param set /car_safety_node features.long_range_enabled false
```

## License

Apache-2.0
