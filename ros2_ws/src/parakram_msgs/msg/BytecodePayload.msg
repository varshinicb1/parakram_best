# A compiled bytecode payload ready for deployment
builtin_interfaces/Time stamp
string device_id          # target board UUID
uint8[] bytecode          # compiled bytecode binary
uint32 instruction_count
string signature_hex      # Ed25519 signature (hex-encoded)
string compiler_version   # backend compiler version
uint32 crc32              # CRC32 checksum of bytecode
