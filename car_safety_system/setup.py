from setuptools import setup
import os
from glob import glob

package_name = 'car_safety_system'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Safety Team',
    maintainer_email='safety@example.com',
    description='ROS 2 car safety system with parameter server support',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'safety_node = car_safety_system.safety_node:main',
            'parameter_demo = car_safety_system.parameter_demo:main',
        ],
    },
)
