cmake_minimum_required(VERSION 3.8)
project(parakram_msgs)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  # Messages (7 types)
  "msg/SensorReading.msg"
  "msg/ActuatorCommand.msg"
  "msg/DeviceStatus.msg"
  "msg/BytecodePayload.msg"
  "msg/DriverEvent.msg"
  "msg/TelemetryFrame.msg"
  "msg/HardwareManifest.msg"
  # Services (3 types)
  "srv/CompileIR.srv"
  "srv/FlashFirmware.srv"
  "srv/QueryDrivers.srv"
  DEPENDENCIES std_msgs builtin_interfaces
)

ament_package()
