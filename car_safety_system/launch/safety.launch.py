#!/usr/bin/env python3
"""
Launch file for the Car Safety System.
Loads parameters from YAML and starts the safety node.
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg_share = get_package_share_directory('car_safety_system')
    default_params = os.path.join(pkg_share, 'config', 'safety_params.yaml')

    params_file_arg = DeclareLaunchArgument(
        'params_file',
        default_value=default_params,
        description='Full path to the ROS 2 parameters YAML file'
    )

    safety_node = Node(
        package='car_safety_system',
        executable='safety_node',
        name='car_safety_node',
        output='screen',
        parameters=[LaunchConfiguration('params_file')],
        emulate_tty=True,
    )

    return LaunchDescription([
        params_file_arg,
        safety_node,
    ])
