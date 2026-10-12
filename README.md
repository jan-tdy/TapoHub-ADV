# Tapo Hub (H100) for Home Assistant

A [HACS](https://hacs.xyz/)-distributable Home Assistant custom integration
for the TP-Link/Tapo **H100** smart hub and its paired child devices
(**T310**/**T315** temperature & humidity sensors, **S200B** buttons).

If you found this useful, please consider giving this repo a star.

## Why this exists

Home Assistant's built-in `tplink` integration cannot talk to the H100 on
current firmware. It fails with:

```
Unsupported device ... encrypt_scheme EncryptionScheme(encrypt_type='TPAP', ...)
```

The H100 (firmware 1.7.10 Build 260725 and later) advertises a `TPAP`
encryption scheme during discovery. The `python-kasa` library bundled with
Home Assistant core (0.10.x) does not implement the TPAP handshake, so the
official integration cannot authenticate to the hub at all — this is a
protocol-support gap, not a bug you can configure around.

This integration exists purely to wire up a **local network, no-cloud**
Home Assistant integration on top of a `python-kasa` fork that *does*
speak TPAP.

## How it works

- **Scope (v1):** the H100 hub and its currently-supported children only
  (T310, T315, S200B). Other TPAP/Tapo device types are out of scope for now.
- **Protocol:** all TPAP handshake and device communication is delegated
  entirely to `python-kasa` — this integration contains no protocol code of
  its own.
- **Entities:** generated dynamically from each device's
  `python-kasa` `Feature` objects (temperature, humidity, battery, RSSI,
  etc.), so new features exposed by the library show up automatically.
  Child devices are registered as separate Home Assistant devices linked to
  the hub via `via_device`.
- **Local only:** this integration does not call any TP-Link/Tapo cloud API
  itself. It does need your TP-Link account email and password once, at
  setup time, because the hub uses them to authenticate the *local* TPAP
  session — no data is sent to the cloud by this code.

## The python-kasa dependency (read this)

This integration pins `python-kasa` to a **specific commit** of an
**unreleased, third-party branch**:

```
python-kasa @ git+https://github.com/ZeliardM/python-kasa.git@e7084472972f08f2e2235b342f3964aedbfaeb3b
```

(`feature/tpap` by [ZeliardM](https://github.com/ZeliardM), based on
[python-kasa/python-kasa#1592](https://github.com/python-kasa/python-kasa/pull/1592).)

This is **not** the official python-kasa project, and TPAP support has not
been merged upstream. Practical consequences:

- The dependency could stop being maintained, be force-pushed, or disappear
  at any time — pinning to a commit SHA (not a branch name) protects you
  from silent changes, but not from the branch vanishing.
- It has not had the same level of review as upstream `python-kasa`.
- When TPAP support lands in upstream `python-kasa` and/or the official
  `tplink` integration, **switch to that** and remove this integration —
  see [MIGRATION.md](MIGRATION.md) for how to do that without losing your
  entity history.

### ⚠️ This silently replaces `python-kasa` for *all* of Home Assistant

Home Assistant installs every custom integration's `requirements` into the
**same shared Python environment** used by core itself — there is no
per-integration isolation. The pinned fork above reports its own version as
`0.10.2`, identical to the official `python-kasa[speedups]==0.10.2` pin used
by the built-in `tplink` integration (and by other integrations that depend
on `python-kasa`, e.g. Tapo vacuum support). Because the version numbers
match, Home Assistant treats the requirement as already satisfied and will
**not** reinstall the official PyPI release afterwards.

In practice this means: once this integration has been installed and Home
Assistant restarted, **every other integration that imports `kasa` now runs
on this unofficial fork too** — not just this one. Several users have
reported that the official `tplink` integration (and Tapo vacuum support)
starts working with TPAP devices after installing this integration and
restarting, purely as a side effect of this shared-dependency override.

This cuts both ways:

- If you only wanted your H100 working with the *official* integration, you
  may not need this integration's entities at all once the fork is
  installed — you can set it up as a HACS integration, confirm the official
  `tplink` integration now works, and then remove this one again (though
  removing it does **not** automatically restore the official `python-kasa`
  release; the fork stays installed until something else forces a
  reinstall — see [Removing this integration](#removing-this-integration-full-rollback)
  below for how to do that safely).
- It also means this integration's "unreleased third-party dependency" risk
  (see above) now applies to every HA integration using `python-kasa`, not
  just this one — if the fork breaks something, it can affect devices this
  integration never touches.

## Installation (HACS)

1. In Home Assistant, open **HACS** in the sidebar.
2. Click the **⋮** (three-dot) menu in the top-right corner → **Custom repositories**.
3. Add:
   - **Repository:** `https://github.com/jan-tdy/TapoHub-ADV`
   - **Type:** Integration
   - Click **Add**.
4. Close the dialog, then search HACS for **"Tapo Hub (H100)"** and open it.
5. Click **Download**, confirm the version, and click **Download** again.
6. Restart Home Assistant (Settings → System → Restart, or use the restart
   prompt HACS shows you).
7. Go to **Settings → Devices & services → + Add integration**, search for
   **"Tapo Hub"**, and select it.
8. Enter the hub's IP address (or leave it blank to search the local
   network) and your TP-Link account email/password.

## Configuration

- **Polling interval:** configurable via the integration's Options (default
  30 seconds).
- **Re-authentication:** if your TP-Link account password changes, Home
  Assistant will prompt you to re-enter credentials.
- **IP address changes:** use the integration's "Reconfigure" option if the
  hub's IP address changes (DHCP reservations are recommended).

## Migrating from the `tplink` integration

If you previously had the H100 partially working (or entities created some
other way) under the `tplink` domain and want your long-term statistics
(e.g. temperature history) to continue, see [MIGRATION.md](MIGRATION.md)
for the exact steps — this must be done manually and is **not** performed
automatically by this integration.

The reverse direction — switching *back* to `tplink` once it supports your
device — is covered in
[MIGRATION.md § Migrating back to the `tplink` integration](MIGRATION.md#migrating-back-to-the-tplink-integration).

## Removing this integration (full rollback)

Removing the integration itself is quick, but **fully reverting the
`python-kasa` dependency swap described above is a separate, extra step** —
skipping it leaves the unofficial fork in place for every integration that
imports `kasa`, even after this integration is gone. There is currently no
"friendly uninstaller" for this; it's always a manual checklist.

> Removing everything below does **not** erase Home Assistant's stored
> history/statistics or your backups — see
> ["What this does and doesn't undo"](#what-this-does-and-doesnt-undo).
> It is not literally "as if it was never installed", just fully removed
> going forward.

### 1. Before you touch anything

- **Create a Home Assistant backup** (Settings → System → Backups → Create
  backup) before changing anything.
- **Write down every entity ID** created by this integration that's used in
  a dashboard or an automation (Settings → Devices & services → Entities,
  filter by integration "Tapo Hub (H100)"). You'll want these if you later
  migrate back to `tplink` — see
  [MIGRATION.md](MIGRATION.md#migrating-back-to-the-tplink-integration).

### 2. Remove the integration's config entries

In **Settings → Devices & services**, open every **Tapo Hub (H100)** entry
and delete it (⋮ → **Delete**) — do this for the hub *and* for any entry
created for a child device. Do this **before** removing the integration
files themselves, otherwise Home Assistant restarts with config entries
that point at code that no longer exists.

### 3. Remove the integration files

- **Installed via HACS:** open HACS → **Tapo Hub (H100)** → ⋮ → **Remove**.
- **Installed manually:** delete only the `custom_components/tapo_hub`
  directory from your config folder. Do not touch any other
  `custom_components/*` folder — several other integrations (e.g. Tapo
  vacuum support) also import `kasa` and are unrelated to this integration's
  files.
- **Optional:** if you don't plan to reinstall this later, you can also
  remove the HACS custom repository entry (HACS → **⋮** → **Custom
  repositories** → remove `jan-tdy/TapoHub-ADV`). This only affects where
  HACS looks for updates; it has no effect on the installed `python-kasa`
  package.

Restart Home Assistant once after this step. The integration is now gone,
but — per the warning earlier in this README — **the `python-kasa` fork is
still installed system-wide** until you do step 4.

### 4. Restore the official `python-kasa` package

This is the step people usually miss. How you do it depends on how your
Home Assistant Python environment is managed, because that determines
*where* the package lives on disk:

- **Home Assistant OS / Supervised:** Home Assistant itself isn't running
  in a Python virtual environment, so pip-installed requirements for
  integrations go into the **`deps`** folder inside your config directory
  (`/config/deps/lib/python3.XX/site-packages/`, where `3.XX` is whatever
  Python version your HA release ships). Use the **Terminal & SSH** add-on
  (or an equivalent shell add-on) to reach this path.
- **Container (official Docker image):** same situation as HAOS — the
  container's Python is not a venv from Home Assistant's point of view, so
  requirements also land under `/config/deps/lib/python3.XX/site-packages/`
  inside the container. Reach it with
  `docker exec -it <container_name> bash` (or the equivalent
  `docker compose exec` command for your setup).
- **Home Assistant Core (legacy manual/venv install):** here Home
  Assistant *is* running inside a Python virtual environment, so
  requirements are installed directly into that venv's own
  `site-packages` (e.g. `/srv/homeassistant/lib/python3.XX/site-packages/`
  for the common `homeassistant` system-user layout — adjust to wherever
  you created your venv). Activate that venv
  (`source /srv/homeassistant/bin/activate`) before running pip commands.

In all three cases, **don't just restart Home Assistant and assume it's
fixed.** Home Assistant only reinstalls a requirement when it decides the
currently-installed one doesn't already satisfy the pinned version — and,
as explained above, the fork reports a version number designed to look
identical to the official release, so a plain restart typically changes
nothing.

**Recommended, non-destructive way to force it back:** remove only the
`kasa` package's own files from that `site-packages` directory — do **not**
delete the whole `deps` folder or venv `site-packages`, since that also
holds dependencies for every *other* custom integration you have installed.
Inside the relevant `site-packages` directory, remove:

- the `kasa/` package directory, and
- the matching `python_kasa-*.dist-info/` (or `kasa-*.dist-info/`) metadata
  directory.

Then restart Home Assistant. With the package now absent, Home Assistant
will reinstall `python-kasa` from whichever manifest(s) in your
installation declare it as a requirement — normally the built-in `tplink`
integration — pulling in **the official PyPI release pinned by your
installed Home Assistant version**, not an arbitrary "latest" version.
(If you'd rather install it yourself immediately instead of waiting for
Home Assistant to do it on restart, find the exact pin for your HA version
in that version's
[`tplink` integration manifest](https://github.com/home-assistant/core/blob/dev/homeassistant/components/tplink/manifest.json)
on GitHub — switch the `dev` branch in that URL to your HA release's tag,
e.g. `2025.x.y` — and `pip install` that exact `python-kasa[speedups]==...`
string into the same `site-packages` path instead of deleting the old
files.)

**Verifying it worked (don't trust the version number alone):** the fork
was built to *report* the same version string as the official release, so
checking `kasa.__version__` by itself proves nothing. Instead check where
the installed package actually came from. From a Home Assistant shell
(Terminal & SSH add-on, `docker exec`, or the activated venv):

```bash
python3 -c "import kasa; print(kasa.__file__)"
cat /path/to/site-packages/python_kasa-*.dist-info/direct_url.json
```

If `direct_url.json` exists and its `url` points at
`github.com/ZeliardM/python-kasa`, the fork is still what's installed,
whatever `kasa.__version__` claims. If that file is absent, or it points
at `pypi.org`/an index rather than a VCS URL, you're on an official,
PyPI-sourced release.

### What this does and doesn't undo

- **Does not erase history:** entity history/long-term statistics already
  recorded in Home Assistant's database, and any backups you made, are
  **not** deleted by removing the integration or its files. This procedure
  is not equivalent to "never installed" — it's a forward removal, not a
  restore-to-factory.
- **May remove TPAP support elsewhere:** per the warning earlier in this
  README, other integrations (the official `tplink` integration, Tapo
  vacuum support) may have only worked with your TPAP-era devices as a
  *side effect* of the fork being installed. Restoring the official
  `python-kasa` package can make those devices stop working again under
  those integrations too, until upstream `python-kasa`/`tplink` gain native
  TPAP support.
- **Don't** delete the entire `deps`/venv `site-packages` directory, edit
  `.storage` files by hand, factory-reset your devices, or build an
  automatic cleanup hook into this integration that swaps dependencies on
  removal — any of those can break other integrations or your device
  pairings in ways that are much harder to undo than this checklist.

If you want to keep a single continuous history graph across the switch
back to `tplink`, see
[MIGRATION.md § Migrating back to the `tplink` integration](MIGRATION.md#migrating-back-to-the-tplink-integration).

## Development

```bash
pip install -r requirements_test.txt
pip install "python-kasa @ git+https://github.com/ZeliardM/python-kasa.git@e7084472972f08f2e2235b342f3964aedbfaeb3b"
pytest
ruff check .
```

`scripts/smoke_test.py` connects to a real hub (host/username/password via
environment variables — never hardcode credentials) and prints its and its
children's features; useful for validating a new pinned commit before
bumping `manifest.json`.

## License

GPL-3.0-or-later — see [LICENSE](LICENSE). This is required because this
integration depends on `python-kasa`, which is itself GPL-3.0-or-later.

Some code patterns (entity/device-registry structure) are adapted from Home
Assistant core's `tplink` integration, licensed Apache-2.0; see the SPDX/
attribution headers in the relevant source files.

## Disclaimer

**English:**

This software is provided "AS IS", without warranty of any kind, express or
implied, including but not limited to the warranties of merchantability,
fitness for a particular purpose, and noninfringement. The author is not
liable for any damage, data loss, device malfunction, bricked firmware, or
any other claim, whether in an action of contract, tort, or otherwise,
arising from, out of, or in connection with the software or the use or
other dealings in the software. **Use at your own risk.**

This project is unofficial and is **not affiliated with, endorsed by, or
supported by TP-Link**. "Tapo" and "TP-Link" are trademarks of their
respective owners and are used here only to identify compatible devices.

This integration depends on an **unreleased, third-party branch** of
`python-kasa` (`feature/tpap` by ZeliardM, based on python-kasa PR #1592).
The author of this integration does not control that code and gives no
guarantee about its correctness, security, or continued availability.
**Installing this integration replaces `python-kasa` system-wide in your
Home Assistant instance** (see the warning above) — this affects every
integration using that library, not just this one.

This integration operates on your **local network only**. You are
responsible for your own credentials, your network's security, and
compliance with TP-Link's terms of service for your devices.

**Slovensky:**

Tento softvér je poskytovaný "TAK AKO JE", bez akejkoľvek záruky, výslovnej
alebo implicitnej, vrátane, nie však výlučne, záruk obchodovateľnosti,
vhodnosti na konkrétny účel a neporušovania práv. Autor nezodpovedá za
žiadnu škodu, stratu dát, poruchu zariadenia, poškodenie firmvéru ("bricking")
ani iný nárok vyplývajúci z používania tohto softvéru. **Používanie je na
vlastné riziko.**

Tento projekt je neoficiálny a **nie je prepojený, podporovaný ani
schválený spoločnosťou TP-Link**. "Tapo" a "TP-Link" sú ochranné známky
príslušných vlastníkov a sú tu použité len na identifikáciu kompatibilných
zariadení.

Táto integrácia závisí od **nevydanej vetvy tretej strany** knižnice
`python-kasa` (`feature/tpap` od ZeliardM, založenej na python-kasa PR
#1592). Autor tejto integrácie tento kód nekontroluje a neposkytuje žiadnu
záruku ohľadom jeho správnosti, bezpečnosti ani ďalšej dostupnosti.
**Inštalácia tejto integrácie nahradí `python-kasa` v celej inštancii Home
Assistant** (pozri varovanie vyššie) — týka sa to každej integrácie, ktorá
túto knižnicu používa, nielen tejto.

Táto integrácia funguje výlučne v **lokálnej sieti**. Za svoje prihlasovacie
údaje, bezpečnosť svojej siete a dodržiavanie zmluvných podmienok TP-Link
pre svoje zariadenia zodpovedá používateľ sám.
