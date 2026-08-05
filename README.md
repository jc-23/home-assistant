# Home Assistant AWTRIX blueprints

Home Assistant automation blueprints for displaying Deutscher Wetterdienst
(DWD) weather warnings on AWTRIX pixel displays.

## Available blueprints

| Firmware | Blueprint version | Support | Blueprint | Import |
|---|---:|---|---|---|
| AWTRIX NG | 1.0.0 | Active development | [DWD weather warnings](blueprints/automation/awtrix_ng_weather_warning_dwd.yaml) | [![Import the AWTRIX NG blueprint into Home Assistant](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fjc-23%2Fhome-assistant%2Fmain%2Fblueprints%2Fautomation%2Fawtrix_ng_weather_warning_dwd.yaml) |
| AWTRIX 3 | 2.0.0 | Maintenance and compatibility fixes | [DWD weather warnings](blueprints/automation/awtrix_weather_warning_dwd.yaml) | [![Import the AWTRIX 3 blueprint into Home Assistant](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fjc-23%2Fhome-assistant%2Fmain%2Fblueprints%2Fautomation%2Fawtrix_weather_warning_dwd.yaml) |

The two files deliberately remain separate. AWTRIX NG uses different MQTT
topics, payload fields, sound commands, validation rules, and restart behavior.
A single universal blueprint would make updates riskier for both user groups.

## Requirements

- Home Assistant with the MQTT integration configured
- The [DWD Weather Warnings integration](https://www.home-assistant.io/integrations/dwd_weather_warnings/)
- AWTRIX connected to the same MQTT broker
- Home Assistant 2024.10 or newer for AWTRIX 3
- Home Assistant 2024.11 or newer and MQTT discovery enabled for AWTRIX NG
- The warning icons from this repository uploaded to each display

## Upload the icons

The upload script supports both firmware generations and detects them
automatically. It requires `bash`, `curl`, `file`, and `jq`.

Download and run the script:

```bash
curl -fsSLO https://raw.githubusercontent.com/jc-23/home-assistant/main/icons/upload_icon.sh
chmod +x upload_icon.sh
./upload_icon.sh --category weather_warning CLOCK_HOST_OR_IP
```

If detection is not possible, specify the firmware explicitly:

```bash
./upload_icon.sh --firmware ng --category weather_warning clock.local
./upload_icon.sh --firmware awtrix3 --category weather_warning 192.0.1.10
```

For an AWTRIX NG device protected by HTTP Basic Auth:

```bash
./upload_icon.sh --user awtrix --category weather_warning clock.local
```

The password is requested without echo. Alternatively, provide it in the
`AWTRIX_PASSWORD` environment variable.

## Configure the blueprint

1. Import the blueprint matching your firmware generation.
2. Create an automation from the imported blueprint.
3. Select one or more AWTRIX devices and one or more DWD warning sensors.
4. Optionally select one or more preliminary-warning sensors.
5. Configure the severity, text, sound, and icon options as needed.

Both blueprints publish the fixed app name `dwd-warnings`. Use one automation
per display or display group and select every region it should show. If more
than one distinct region is selected, each warning is prefixed with the region
name. Leading `Gemeinde`, `Stadt`, and `Hansestadt` labels are removed to keep
the display text compact. A current-warning and preliminary-warning sensor for
the same region count as one region.

When updating an older AWTRIX 3 installation, restart the display once after
the first `2.0.0` publish. This removes the former app from memory.

The beep is sent only when a warning newly reaches the configured minimum level
or an existing warning escalates.

## Migrating an automation from AWTRIX 3 to AWTRIX NG

Do not replace the source URL of an imported AWTRIX 3 blueprint. Instead:

1. Upload the icons to AWTRIX NG using the new file API or the upload script.
2. Import the separate AWTRIX NG blueprint.
3. Create a new automation and copy the relevant choices from the old one.
4. Verify the display, icon behavior, and optional sound.
5. Disable or remove the old AWTRIX 3 automation.

See the official
[AWTRIX NG migration guide](https://blueforcer.github.io/awtrix-ng/guides/migrating-from-awtrix3/)
for the firmware-level changes.

## Version and support policy

- Each blueprint has its own semantic version at the beginning of its
  description. The versions can advance independently.
- The AWTRIX 3 file keeps its existing filename and input identifiers so
  re-importing it does not force users onto AWTRIX NG.
- AWTRIX 3 receives maintenance and Home Assistant compatibility fixes.
- New AWTRIX functionality is developed in the AWTRIX NG blueprint.
- The stable `main` URLs above are the update channels used for blueprint
  imports.

## Development and validation

Install the development dependencies and run the checks:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests -v
yamllint blueprints/automation/*.yaml
bash -n icons/upload_icon.sh
```

The tests render representative AWTRIX 3 and AWTRIX NG payloads from an
anonymized [DWD attributes fixture](tests/fixtures/dwd_warning_attributes.yaml),
exercise multi-region, change, and beep detection, and check the
firmware-specific MQTT topics.

## Credits

The original blueprint is based on Jeef's
[AWTRIX Weather and Forecast blueprint](https://github.com/jeeftor/HomeAssistant/blob/master/blueprints/automation/awtrix_weatherflow.yaml).
