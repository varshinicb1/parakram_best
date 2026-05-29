# Command to write a value to an actuator driver
builtin_interfaces/Time stamp
string driver_name        # e.g. "drv_relay"
string capability         # e.g. "on_off"
float64 value             # numeric value to write
string device_id          # target board UUID
uint32 timeout_ms         # max wait for acknowledgment (0 = fire-and-forget)
