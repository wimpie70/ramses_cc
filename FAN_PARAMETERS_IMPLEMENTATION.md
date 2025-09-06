# Ramses CC Fan Parameter Controller Implementation

## Overview
This document outlines the implementation strategy for adding fan parameter control to the Ramses CC integration. The approach uses a dedicated parameter controller device linked to each fan, controlled via a fake remote device. The implementation includes automatic parameter synchronization and real-time updates through message listening.

## Architecture

```
┌─────────────────┐     ┌───────────────────────┐     ┌─────────────────────┐
│                 │     │                       │     │                     │
│  Fan Device     │◄────┤  Parameter Controller ├────►│  Fake Remote Device │
│  (e.g., 01:1234)│     │  (01:1234_params)     │     │  (e.g., FA:KE01)    │
│                 │     │                       │     │                     │
└─────────────────┘     └───────────────────────┘     └─────────────────────┘
```

## Implementation Phases

ramses_rf
- PR #1 add get_fan_param() method to ramses_rf has been subitted: #198
- PR #2 add set_fan_param() method to ramses_rf has been subitted: #199 committed to fix linter errors also for 198

ramses_cc
- PR #1 add get_fan_param() method to ramses_cc has been subitted: #256
- PR #2 add set_fan_param() method to ramses_cc has been subitted: #257

done:
            ### phase 2: communication layer (PR #2)

            1. **Communication Layer** (broker.py)
            x this may need some extra PR for ramses_rf
            x Add `set_fan_param` W command to broker.py (set_fan_param() in ~/dev/ramses_rf/src/ramses_tx/command.py)
            x Add `set_fan_param` as a service in __init__.py

            2. **test files**
            x add tests for communication layer

### Phase 3: DIS Device Parameter Controller (ramses_rf PR #3)

This phase implements the DIS device as the primary controller for fan parameters, following the event-driven architecture pattern preferred by Home Assistant.

1. **Inventory**

    - check HvacDisplayRemote for DIS devices
    - create on initial setup
    - update on config_flow changes ?? check if config flow changes require a restart...then we don't need this
    - check if DIS id is bound to a fan device (when faked)
    - ramses_rf: get_fan_param() and set_fan_param()
    - ramses_rf: _2411_PARAMS_SCHEMA (for parameter registry) (ramses_rf/src/ramses_tx/ramses.py)
    - we need 2 PR's : DIS and HVac

2. **Ramses_rf DIS Implementation**


ramses_rf PR #4: Core DIS Command Support
Title: "Add DIS device support for fan parameter commands"

Scope:

Add
get_fan_param()
 and
set_fan_param()
 to
HvacDisplayRemote
 class
Add basic unit tests for command construction
Document the new DIS device capabilities
Add any necessary command parsing utilities
Exclude: Actual parameter value storage/state management
Benefits:

Self-contained changes
Easy to review
Low risk of breaking existing functionality
Provides foundation for next PR


Title: "Add FAN device parameter state management"

Add parameter storage to HvacVentilator class
Implement 2411 message handling
Add event emission for parameter changes
Add capability detection
Add comprehensive tests for state management
Document the parameter handling architecture








### phase 5: ramses_cc DIS implementation (_cc PR #3)
1. **Parameter Entities** (fan_parameters.py)
   - Implement base parameter entity class
   - Add number entities for numeric parameters
   - Add select entities for enumerated parameters
   - Implement sensor-based change detection (see snippets.py.txt)
   - Fire events on actual value changes
   - Include old/new values in change events
   - Add debouncing for rapid updates

2. **Parameter Registry**
   - Create parameter definitions
   - Implement parameter metadata
   - Add validation logic

3. **test files**
   - add tests for parameter entities
   - add tests for parameter registry

### phase 6: integration & testing (PR #5)
1. **Broker Integration**
   - Connect parameter controllers to broker
   - Implement device discovery only when config_flow is changed, so only on first setup
   - Add error handling

2. **Testing**
   - Unit tests for parameter entities
   - Integration tests with fake devices
   - Documentation updates

### dev env
venv313
https://github.com/zxdavb/ramses_cc/wiki/7.-How-to-submit-a-PR
https://github.com/zxdavb/ramses_cc
docker hass start
~/dev/ramses_cc current working directory
~/dev/ramses_rf 0.50.2 (PR #198 with get_fan_param command)
/home/willem/dev/2411 codes.txt



## Detailed Implementation

## PR #2: Fan Parameter Events

### Event Structure

When a fan parameter is updated, the integration fires a `ramses_cc_fan_param_updated` event with the following structure:

```python
{
    'device_id': '32:123456',          # Device ID of the fan
    'param_id': '4E',                  # Parameter ID (2 hex digits)
    'value': 1,                        # Parameter value
    'description': 'Moisture scenario position (0=medium, 1=high)',
    'raw_payload': "{'parameter': '4E', 'description': 'Moisture scenario...}",
    'source': '32:153289 (FAN)',       # Source device that sent the update
    'timestamp': '2025-07-11T10:30:45.123456'  # ISO format timestamp
}
```

### Example Automation

```yaml
automation:
  - alias: "Fan Parameter Changed"
    trigger:
      platform: event
      event_type: ramses_cc_fan_param_updated
      event_data:
        device_id: "32:123456"  # Optional filter
        param_id: "4E"          # Optional filter
    action:
      service: notify.notify
      data:
        title: "Fan Parameter Updated"
        message: >
          Fan {{ trigger.event.data.device_id }}
          Parameter: {{ trigger.event.data.param_id }} ({{ trigger.event.data.description }})
          New value: {{ trigger.event.data.value }}
```

### Testing PR #2

1. **Verify Event Reception**:
   - Enable debug logging for the ramses_cc component
   - Trigger a fan parameter change
   - Check logs for `Firing ramses_cc_fan_param_updated event`
   - Verify the event data structure is correct

2. **Test with Different Parameters**:
   - Test with different parameter IDs
   - Verify both numeric and string parameter values
   - Check that the description is included when available

3. **Test Event Filtering**:
   - Create automations with different event_data filters
   - Verify they trigger only for matching parameters

4. **Error Cases**:
   - Test with invalid parameter IDs
   - Verify graceful handling of malformed messages


### 1. Schema Updates (`schemas.py`)
```python
# Add to fan schema
FAN_SCHEMA = {
    vol.Optional(CONF_PARAM_REMOTE): cv.matches_regex(REGEX_DEVICE_ID),
    # ... existing options
}
```






@fan_rate.setter
def fan_rate(self, value: int) -> None:
    cmd = Command.set_fan_mode(self.id, int(4 * value), src_id=self.id)
    self._gwy.send_cmd(cmd, num_repeats=2, priority=Priority.HIGH)


class HvacDisplayRemote(HvacRemote):  # DIS
    """The DIS (display switch)."""

    _SLUG: str = DevType.DIS

    async def get_fan_param(self, fan_id: str, param_id: str) -> Any:
        """Get a fan parameter through this DIS device."""
        cmd = Command.get_fan_param(
            fan_id=fan_id,
            param_id=param_id,
            src_id=self.id
        )
        return await self._gwy.send_cmd(cmd)

    async def set_fan_param(self, fan_id: str, param_id: str, value: Any) -> None:
        """Set a fan parameter through this DIS device."""
        cmd = Command.set_fan_param(
            fan_id=fan_id,
            param_id=param_id,
            value=value,
            src_id=self.id
        )
        await self._gwy.send_cmd(cmd)


class RamsesFanParameterEntity(RamsesEntity):
    def __init__(self, broker, fan_device, dis_device, parameter_id):
        super().__init__(broker, fan_device, entity_description)
        self._dis_device = dis_device
        self._parameter_id = parameter_id

    async def async_update(self):
        value = await self._dis_device.get_fan_param(
            fan_id=self._device.id,
            param_id=self._parameter_id
        )
        self._attr_native_value = value

    async def async_set_value(self, value):
        await self._dis_device.set_fan_param(
            fan_id=self._device.id,
            param_id=self._parameter_id,
            value=value
        )

## Testing Strategy

1. **Unit Tests**
   - Parameter value validation and conversion
   - Message parsing and generation
   - Entity state updates
   - Error conditions and recovery

2. **Integration Tests**
   - Full parameter lifecycle (read/write)
   - Message listener registration
   - Concurrent access handling
   - Error recovery scenarios

3. **Manual Testing**
   - Real device verification
   - Long-running stability
   - Error recovery under network issues

## Future Enhancements

1. **Parameter Presets**
   - Save/load parameter sets
   - Quick-apply configurations

2. **Advanced Validation**
   - Parameter dependencies
   - Value constraints
   - Read-only parameters

3. **UI Improvements**
   - Custom dashboard cards
   - Parameter grouping
   - Visual feedback
