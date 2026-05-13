import os
import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    pkg_mentorpia1 = get_package_share_directory('mentorpia1_simulator')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # Xacro -> URDF
    xacro_file = os.path.join(pkg_mentorpia1, 'urdf', 'mentorpi.xacro')
    robot_description_config = xacro.process_file(xacro_file)
    robot_description = {'robot_description': robot_description_config.toxml()}

    # Set Gazebo resource path to find meshes
    # In Gazebo Sim (Ignition), we use GZ_SIM_RESOURCE_PATH
    gz_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=[os.path.join(pkg_mentorpia1, '..')]
    )

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='both',
        parameters=[robot_description, {'use_sim_time': use_sim_time}],
    )

    # Gazebo Sim (headless by default if you don't run Gazebo GUI, but here we specify -s for server only)
    # Actually, we let the user decide. But since you asked for no GUI, I'll add an argument.
    headless = LaunchConfiguration('headless')
    declare_headless_cmd = DeclareLaunchArgument(
        'headless',
        default_value='True',
        description='Whether to run Gazebo GUI'
    )

    # We use gz_sim.launch.py which is the recommended way
    # If headless is True, we pass -s
    gz_args = LaunchConfiguration('gz_args')
    declare_gz_args_cmd = DeclareLaunchArgument(
        'gz_args',
        default_value='-r empty.sdf',
        description='Gazebo arguments'
    )

    # We'll construct gz_args based on headless
    from launch.substitutions import PythonExpression
    gz_args_value = PythonExpression([
        "'-r empty.sdf' + (' -s' if '", headless, "' == 'True' else '')"
    ])
    
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': gz_args_value}.items(),
    )

    # Spawn Robot
    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'mentorpia1',
            '-string', robot_description_config.toxml(),
            '-z', '0.1',
        ],
        output='screen'
    )

    # Bridge
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
            '/lidar@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
            '/camera@sensor_msgs/msg/Image[gz.msgs.Image',
            '/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
            '/imu@sensor_msgs/msg/Imu[gz.msgs.IMU',
            '/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
            '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
            '/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model',
        ],
        output='screen'
    )

    # Ackermann Converter
    ackermann_to_twist = Node(
        package='mentorpia1_simulator',
        executable='ackermann_to_twist',
        name='ackermann_to_twist',
        output='screen',
        parameters=[{'wheelbase': 0.14}],
    )

    return LaunchDescription([
        gz_resource_path,
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        declare_headless_cmd,
        declare_gz_args_cmd,
        gazebo,
        spawn,
        robot_state_publisher,
        bridge,
        ackermann_to_twist,
    ])
