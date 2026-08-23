#!/usr/bin/env python3
"""
Small helper node that demonstrates interacting with the
car_safety_node parameter server from another node.
"""

import rclpy
from rclpy.node import Node
from rcl_interfaces.srv import GetParameters, SetParameters, ListParameters
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue


class ParameterDemo(Node):
    def __init__(self):
        super().__init__('parameter_demo')
        self.client_get = self.create_client(GetParameters, '/car_safety_node/get_parameters')
        self.client_set = self.create_client(SetParameters, '/car_safety_node/set_parameters')
        self.client_list = self.create_client(ListParameters, '/car_safety_node/list_parameters')

        self.get_logger().info('Waiting for car_safety_node parameter services...')
        self.client_get.wait_for_service(timeout_sec=10.0)
        self.client_set.wait_for_service(timeout_sec=5.0)
        self.client_list.wait_for_service(timeout_sec=5.0)
        self.get_logger().info('Services available – running demo')

        self.create_timer(1.0, self._run_demo_once)
        self.done = False

    def _run_demo_once(self):
        if self.done:
            return
        self.done = True

        # 1. List parameters
        self.get_logger().info('--- Listing parameters ---')
        req = ListParameters.Request()
        future = self.client_list.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)
        if future.result():
            names = future.result().result.names
            self.get_logger().info(f'Found {len(names)} parameters')
            for n in sorted(names)[:8]:
                self.get_logger().info(f'  • {n}')
            if len(names) > 8:
                self.get_logger().info(f'  ... and {len(names)-8} more')

        # 2. Read a few values
        self.get_logger().info('--- Reading selected parameters ---')
        req = GetParameters.Request()
        req.names = [
            'hands_off.timeout_sec',
            'health.hr_critical_high',
            'long_range.min_ttc_sec',
            'features.hands_off_enabled'
        ]
        future = self.client_get.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)
        if future.result():
            for name, val in zip(req.names, future.result().values):
                self.get_logger().info(f'  {name} = {self._param_value_to_str(val)}')

        # 3. Change a parameter at runtime
        self.get_logger().info('--- Setting hands_off.timeout_sec to 1.8 ---')
        req = SetParameters.Request()
        p = Parameter()
        p.name = 'hands_off.timeout_sec'
        p.value = ParameterValue(type=ParameterType.PARAMETER_DOUBLE, double_value=1.8)
        req.parameters = [p]
        future = self.client_set.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)
        if future.result():
            results = future.result().results
            if results and results[0].successful:
                self.get_logger().info('Parameter change accepted by safety node')
            else:
                reason = results[0].reason if results else 'unknown'
                self.get_logger().warn(f'Parameter change rejected: {reason}')

        self.get_logger().info('Parameter demo finished')

    @staticmethod
    def _param_value_to_str(val: ParameterValue) -> str:
        if val.type == ParameterType.PARAMETER_BOOL:
            return str(val.bool_value)
        if val.type == ParameterType.PARAMETER_INTEGER:
            return str(val.integer_value)
        if val.type == ParameterType.PARAMETER_DOUBLE:
            return str(val.double_value)
        if val.type == ParameterType.PARAMETER_STRING:
            return val.string_value
        return f'<type {val.type}>'


def main(args=None):
    rclpy.init(args=args)
    node = ParameterDemo()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
