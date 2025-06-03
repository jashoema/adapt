# NAPALM to Netmiko Migration Notes

ADAPT has been migrated from using NAPALM to Netmiko for network device interaction. This document outlines the key changes and considerations.

## Reasons for Migration

1. **Simplicity**: Netmiko offers a more straightforward approach to sending commands to network devices
2. **Wider device support**: Netmiko supports a broader range of devices and platforms
3. **Active development**: Netmiko is actively maintained and regularly updated
4. **Consistent interface**: Provides a consistent way to interact with different network device types
5. **Better error handling**: More detailed error messages and better exception handling

## Key Changes

### Connection Initialization

- Changed from NAPALM's driver-based approach to Netmiko's ConnectHandler
- Updated device type mapping from NAPALM's format to Netmiko's format (e.g., 'ios' -> 'cisco_ios')
- Simplified connection process by using ConnectHandler's built-in capabilities

### Command Execution

- Replaced NAPALM's `cli()` method with Netmiko's `send_command()` method
- Replaced NAPALM's configuration workflow (load_merge_candidate, compare_config, commit_config) with Netmiko's simpler `send_config_set()` method
- Improved error handling and output formatting

### Device Facts Collection

- Added new utility module `netmiko_utils.py` for parsing device facts from command output
- Implemented platform-specific parsing logic for different device types
- Enhanced interface detection for various network platforms

### Configuration Format

- Updated the example inventory YAML file to reflect Netmiko-specific parameters
- Removed NAPALM-specific parameters while maintaining backward compatibility where possible

## Usage Notes

- The device_type in the inventory file maps to Netmiko's device types (see [Netmiko documentation](https://github.com/ktbyers/netmiko/blob/develop/PLATFORMS.md) for the full list)
- Optional arguments like 'secret' (enable password) are still supported
- Error messages have been updated to refer to Netmiko instead of NAPALM
- The behavior of the save_config functionality is now device-dependent

## Future Enhancements

- Add support for advanced Netmiko features like:
  - SSH key-based authentication
  - Session logging
  - Using TextFSM templates for structured data parsing
  - Auto-detection of device types
