# Status heartbeat from a connected device
builtin_interfaces/Time stamp
string device_id          # board UUID
string firmware_version   # e.g. "1.0.0"
uint8 status              # 0=offline, 1=connected, 2=running, 3=error, 4=ota_in_progress
uint32 uptime_seconds
uint8 battery_percent     # 0-100 (255 = not applicable)
int8 rssi_dbm             # WiFi/BLE signal strength
uint16 free_heap_kb
string[] active_drivers   # currently loaded driver names
