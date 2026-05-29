# A single sensor reading from any driver
builtin_interfaces/Time stamp
string driver_name        # e.g. "drv_bme280"
string capability         # e.g. "temperature"
float64 value             # numeric reading
string unit               # e.g. "celsius", "percent", "ppm"
uint8 quality             # 0-100 signal quality
string device_id          # board UUID
