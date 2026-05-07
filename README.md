# Rinnai Smart for Home Assistant

Home Assistant custom integration for Rinnai Smart water heaters in China.

This fork is based on `catro/rinnai_smart` and adds compatibility work for
`RUS-UR16E75G-CY` / `RUS-**E75G-CY` devices.

## WARNING

* **RINNAI DOESN'T PROVIDE ANY OFFICIALLY SUPPORTED API, THUS THEIR CHANGES MAY BREAK HASS INTEGRATIONS AT ANY TIME.**
* **USE IT AS YOUR OWN RISK. YOUR ACCOUNT MAY BE BANNED.**
* **THIS INTEGRATION IS IN ALPHA STATE. ONCE CONNECTION LOST, RECONFIGURE THE DEVICE AGAIN.**

## IMPORTANT NOTES

* The upstream integration was originally written for `RUS-R16E86FBF`.
* This fork has been tested against `RUS-UR16E75G-CY`.
* Rinnai does not publish a stable API; other models may use different field encodings.
* Use Home Assistant logs and the `rinnai_raw` water heater attribute when validating a new model.

## RUS-UR16E75G-CY Notes

This model differs from the original E86 mapping in a few important places:

- Temperature values may be reported as little-endian hex-like strings, for example `2800` means `40`.
- Switch-like values may use `31` for on and `30` for off, instead of `01` and `00`.
- `operationMode=00` does not necessarily mean the heater is powered off on this model.
- The water heater entity exposes a `rinnai_raw` attribute with the raw `processParameter` payload for debugging.

Observed mappings:

- `power=31`: heater is on.
- `temporaryCycleInsulationSetting=31`: one-key circulation is on.
- `temporaryCycleInsulationSetting=30`: one-key circulation is off.
- `cycleReservationSetting=30`: circulation reservation is off.

### Features

- water heater:
    * set operating temperature (&deg;C)
    * set operating mode
- set recirculation mode
- set recirculation reservation
- set temporary recirculation
- multiple Rinnai devices

![](./screenshot.png)

## Installation

#### Versions

The 'main' branch of this custom component is considered unstable, alpha quality and not guaranteed to work.
Please make sure to use one of the official release branches when installing using HACS, see [what has changed in each version](https://github.com/keli/rinnai_smart/releases).

Recommended release for `RUS-UR16E75G-CY`: `v0.0.5-e75gcy.1`.

#### With HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=keli&repository=rinnai_smart&category=integration)

#### Manual
1. Copy the `rinnai_smart` directory from `custom_components` in this repository and place inside your Home Assistant's `custom_components` directory.
2. Restart Home Assistant
3. Follow the instructions in the `Setup` section

> [!WARNING]
> If installing manually, in order to be alerted about new releases, you will need to subscribe to releases from this repository.

# Setup
[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=rinnai)

> [!Tip]
> If you are unable to use the button above, follow the steps below:
> 1. Navigate to the Home Assistant Integrations page `(Settings --> Devices & Services)`
> 2. Click the `+ ADD INTEGRATION` button in the lower right-hand corner
> 3. Search for `Rinnai Smart`
