# Easy PV (EW)

> Fork of [BigBoot/ha-easy-pv](https://github.com/BigBoot/ha-easy-pv), focused on the EW VN2T08EU.
> Uses the domain `easy_pv_ew`, so it can be installed alongside the original.

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]

Home Assistant integration for microinverters using the Easy PV app by Shanghai Electronics Way Co. and possibly other rebranded versions.

![logo][logo]

Supported devices:
- EW - Electronic Way VN2T10EU / VN2T08EU / VN2T06EU ✅
- Hatch Solar HSEU-600D/800D/1000D/HSEU-300S/400S/500S ⚠️ (Untested)
- Probably more if your app looks like this chances are it will work: ![app][app]


## Installation

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

Using your HA configuration directory (folder) as a starting point you should now also have this:

```text
custom_components/easy_pv_ew/sensor.py
custom_components/easy_pv_ew/device_tracker.py
custom_components/easy_pv_ew/strings.json
custom_components/easy_pv_ew/utils.py
custom_components/easy_pv_ew/translations
custom_components/easy_pv_ew/translations/en.json
custom_components/easy_pv_ew/translations/de.json
custom_components/easy_pv_ew/quality_scale.yaml
custom_components/easy_pv_ew/config_flow.py
custom_components/easy_pv_ew/__init__.py
custom_components/easy_pv_ew/model.py
custom_components/easy_pv_ew/easy_pv/__init__.py
custom_components/easy_pv_ew/manifest.json
custom_components/easy_pv_ew/coordinator.py
custom_components/easy_pv_ew/entity.py
custom_components/easy_pv_ew/const.py
```

## Configuration is done in the UI

## Development

The devcontainer (`.devcontainer/devcontainer.json`) bind-mounts a host folder to `/workspaces/austausch`. The source is taken from the host environment variable `HA_AUSTAUSCH` (`${localEnv:HA_AUSTAUSCH}`), which must be set on the machine running VS Code before VS Code starts. The folder must exist on the host, otherwise the container does not start; set the variable and create the folder, or adjust/remove the mount before opening the container.

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

## Credits

Code template was mainly taken from [@Ludeeus](https://github.com/ludeeus)'s [integration_blueprint][integration_blueprint] template

---

[integration_blueprint]: https://github.com/custom-components/integration_blueprint
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[logo]: logo.svg
[app]: app.png
[license-shield]: https://img.shields.io/github/license/michael-hagmann/ha-easy-pv-ew.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40michael--hagmann-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/michael-hagmann/ha-easy-pv-ew.svg?style=for-the-badge
[releases]: https://github.com/michael-hagmann/ha-easy-pv-ew/releases
[user_profile]: https://github.com/michael-hagmann
