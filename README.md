# Easy PV (EW)

> Fork of [BigBoot/ha-easy-pv](https://github.com/BigBoot/ha-easy-pv), focused on the EW VN2T08EU.
> Uses the domain `easy_pv_ew`, so it can be installed alongside the original.
>
> This is a community project, not affiliated with Electronic Way or the makers of the Easy PV app.

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]

Home Assistant integration for microinverters using the Easy PV app by Shanghai Electronics Way Co. and possibly other rebranded versions.

![logo][logo]

Supported devices:
- EW - Electronic Way VN2T08EU ✅ (tested with this fork)
- EW - Electronic Way VN2T10EU / VN2T06EU (listed as supported by the original integration, untested with this fork)
- Hatch Solar HSEU-600D/800D/1000D/HSEU-300S/400S/500S ⚠️ (Untested)
- Probably more devices that are set up with the Easy PV app (untested)


## Installation

Requires Home Assistant 2026.10 or newer.

### HACS (Recommended)

Installation is via the [Home Assistant Community Store
(HACS)](https://hacs.xyz/), which is the best place to get third-party
integrations for Home Assistant. Once you have HACS set up, simply click the button below or
follow the [instructions for adding a custom
repository](https://hacs.xyz/docs/faq/custom_repositories) and then
the integration will be available to install like any other.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=michael-hagmann&repository=ha-easy-pv-ew&category=integration)

### Manual

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `easy_pv_ew`.
4. Download _all_ the files from the `custom_components/easy_pv_ew/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Easy PV (EW)"

The folder must contain `manifest.json` directly, e.g. `custom_components/easy_pv_ew/manifest.json`, together with all other files and subfolders (`easy_pv/`, `translations/`).

## Configuration

Go to **Settings → Devices & services → Add integration** and search for **Easy PV (EW)**.

| Parameter | Description |
| --- | --- |
| Username | Phone number or email address you use to log in to the Easy PV app |
| Password | Password of the Easy PV app |

The credentials are used once to log in. Only the login token returned by the cloud is stored, not the password. Each Easy PV account can be added once.

### Options

**Settings → Devices & services → Easy PV (EW) → Configure**

| Option | Default | Description |
| --- | --- | --- |
| Scan interval | 60 s | How often the Easy PV cloud is polled, 60 to 240 seconds. Polling more often than every 60 seconds is not possible, to spare the manufacturer's servers. |

## Entities

One device is created per station, per inverter and per PV input (MPPT), linked to each other.

| Device | Entities |
| --- | --- |
| Station | Power (W), energy today, lifetime energy (kWh); location (diagnostic) |
| Inverter | Power (W), energy today, energy this month, lifetime energy (kWh), grid voltage (V); online, fault, firmware versions (diagnostic) |
| PV input | Power (W), voltage (V), current (A); temperature, grid frequency (diagnostic, disabled by default: the VN2T08EU does not report them) |

Energy sensors use `state_class: total_increasing` and power, voltage and current use `measurement`, so all of them have long-term statistics. For the Energy dashboard (*Solar production*) use the **lifetime energy of the station**: it counts since the station was created and continues after a new registration of the inverter. The lifetime energy of the inverter counts only since the inverter was last registered in the Easy PV app.

A diagnostics download (**Settings → Devices & services → Easy PV (EW) → ⋮ → Download diagnostics**) contains the last raw cloud response with serial numbers, location, account data and tokens removed.

## Data updates

The integration polls the Easy PV cloud (`cloud_polling`); there is no local interface on the inverter. Every scan interval it reads the station list and the data of each inverter, one after another.

- **Short cloud outages** (e.g. brief network problems) are bridged: the last valid values are kept for up to 5 minutes, after that the entities become unavailable.
- **Offline or faulty inverter:** the inverter switches off when the modules deliver too little power, so the cloud reports it offline every night. While it is offline or faulty, live values (power, voltage, current, temperature, frequency) are unavailable. Energy counters stay available.
- **PV inputs at night:** after midnight (time zone of the station) the cloud stops reporting the PV inputs until the inverter is online again. Their entities become unavailable and come back with the next data.
- **Lifetime energy of the station never goes backwards:** a lower value from the cloud (around midnight the cloud reports it briefly lower and then 0.01 kWh below the previous value until the next yield) is ignored and the last value is kept until the cloud exceeds it again. If the lower value lasts a day, a warning is logged once.
- **Lifetime energy of the inverter** behaves the same, but a lower non-zero value that persists for 24 hours is accepted as a real reset (the inverter counts from 0 again after a new registration in the app); 0 is never accepted.
- **Energy this month** ignores the brief 0 the cloud reports at midnight; a lower value is only taken over on the first day of a month or after a change of month, in the time zone of the station.
- **Unexpected responses:** every response is checked for missing fields, wrong types and implausible values. Such values are ignored (the entity becomes unavailable) and a warning is logged once per field until the next restart.
- New inverters and PV inputs are added automatically.

## Known limitations

- Works only through the Easy PV cloud; without internet access there are no values. The cloud API is not officially documented and may change without notice.
- Accuracy depends on the inverter: an independent test found the app values 8–10 % lower than a reference meter. The integration shows the cloud values unchanged.
- The lifetime energy of the inverter starts again at 0 when the inverter is registered anew in the Easy PV app; the station total continues.
- The cloud resets the daily and monthly energy at midnight in the time zone set for the station in the app (e.g. UTC), which may differ from your local time.
- The login token cannot be refreshed. When it expires, the entities become unavailable and Home Assistant asks you to re-authenticate (**Settings → Devices & services**).
- The location tracker of a station shows the zone (e.g. `home`), not the address.

## Troubleshooting

- **"Failed to connect to the Easy PV cloud":** check that Home Assistant can reach the internet; the cloud may also be down temporarily. The integration retries on its own.
- **"Invalid username or password":** use the same phone number or email address and password as in the Easy PV app.
- **Re-authentication required:** the token has expired; open **Settings → Devices & services**, choose *Reconfigure* on Easy PV (EW) and enter the app credentials again.
- **Warnings "Unexpected Easy PV API response":** the cloud API may have changed. Please open an issue with the warning text and the diagnostics download.
- For details, enable debug logging on the integration page (**Enable debug logging**). Raw responses are logged with personal data removed.

## Removal

1. **Settings → Devices & services → Easy PV (EW)**, open the menu (⋮) and choose **Delete**. This removes all devices and entities of the account; the long-term statistics remain in the database.
2. Optional: remove the integration in HACS (**HACS → Easy PV (EW) → Remove**) or delete the folder `custom_components/easy_pv_ew`, then restart Home Assistant.

A single inverter or PV input can be deleted on its device page once the cloud no longer reports it. Because the PV inputs are missing at night, deleting them is offered then as well; a deleted PV input is created again when the cloud reports it.

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

## Credits

Code template was mainly taken from [@Ludeeus](https://github.com/ludeeus)'s [integration_blueprint][integration_blueprint] template

---

[integration_blueprint]: https://github.com/custom-components/integration_blueprint
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[logo]: custom_components/easy_pv_ew/brand/icon.png
[license-shield]: https://img.shields.io/github/license/michael-hagmann/ha-easy-pv-ew.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40michael--hagmann-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/michael-hagmann/ha-easy-pv-ew.svg?style=for-the-badge
[releases]: https://github.com/michael-hagmann/ha-easy-pv-ew/releases
[user_profile]: https://github.com/michael-hagmann
