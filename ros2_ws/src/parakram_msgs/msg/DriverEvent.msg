# Event emitted by a firmware driver (interrupt, threshold, fault)
builtin_interfaces/Time stamp
string device_id
string driver_name
uint8 event_type          # 0=data_ready, 1=threshold, 2=fault, 3=init_complete, 4=deinit
string payload_json       # event-specific data as JSON string
uint32 sequence_number    # monotonic per-driver counter
