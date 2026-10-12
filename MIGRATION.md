# Migrating entity IDs and history after switching to this integration

This integration uses its own domain (`tapo_hub`), so its entities get
**new** entity IDs and therefore start **new**, empty long-term statistics
(e.g. temperature/humidity graphs reset to zero history).

If you want existing graphs to keep their history, the simplest approach is
to **rename the new entities to the old entity IDs** and delete the old
integration's (now orphaned) entities first, so the IDs are free. Home
Assistant's long-term statistics are keyed by entity_id, so once the new
entity takes over the old entity_id, the existing graph continues.

> This is a manual, one-time procedure. It is **not** performed
> automatically by this integration, and there is no supported way to
> "merge" two separate statistics series after the fact — renaming to reuse
> the old entity_id is the easiest way to keep a single continuous graph.

## Procedure

1. **Set up this integration first** and confirm the H100 hub and its
   children (T310/T315/S200B) show up correctly with live data, before
   touching the old integration.

2. **Note down the old entity IDs** you want to preserve history for, e.g.:

   | Old entity_id (under `tplink`)              | New entity_id (under `tapo_hub`)             |
   |-----------------------------------------------|-----------------------------------------------|
   | `sensor.<old_temp_sensor_entity_id>`          | `sensor.<new_temp_sensor_entity_id>`          |
   | `sensor.<old_humidity_sensor_entity_id>`      | `sensor.<new_humidity_sensor_entity_id>`      |
   | `binary_sensor.<old_battery_entity_id>`       | `binary_sensor.<new_battery_entity_id>`       |
   | `sensor.<old_rssi_entity_id>`                 | `sensor.<new_rssi_entity_id>`                 |

   (Replace the placeholders with your actual entity IDs — check
   Settings → Devices & services → Entities, filtered by integration.)

3. **Remove the old `tplink` config entry** for this hub (Settings → Devices
   & services → the old "TP-Link Smart Home" entry → ⋮ → Delete). This frees
   up the old entity IDs. Do this only once you've confirmed the new
   integration works — statistics for the old entities are preserved in the
   database even after the entity itself is removed, as long as you don't
   also purge them.

4. **Rename the new entities to the freed old entity IDs**: for each entity
   in the table above, go to Settings → Devices & services → Entities, open
   the new `tapo_hub` entity, click the gear icon, and change its Entity ID
   to the old one. Home Assistant will now attach the entity's ongoing
   updates to the existing statistics series, so the graph continues rather
   than resetting.

5. **Verify**: open the relevant history graph/dashboard card and confirm
   it shows a continuous line across the switchover point (there may be a
   short gap corresponding to the time the old integration was removed and
   the new one renamed).

## If you'd rather keep both histories separate

If preserving a single continuous graph isn't important to you, you can
skip all of the above — just remove the old `tplink` entry and let the new
`tapo_hub` entities create fresh statistics under their own entity IDs.

## Migrating back to the `tplink` integration

This is the mirror image of the procedure above, for when you want to drop
this integration and go back to the official `tplink` integration — for
example once upstream `python-kasa`/`tplink` gain native TPAP support, or
after confirming you don't need this integration's entities at all (see the
shared-dependency section in [README.md](README.md)).

> **This assumes `python-kasa` has already been restored to an official
> release.** Follow
> [README.md § Removing this integration](README.md#removing-this-integration-full-rollback)
> first — the `tapo_hub` → `tplink` entity switch below is pointless while
> the unofficial fork is still what Home Assistant imports as `kasa`.

### 1. Confirm `tplink` actually supports your device now

Don't assume the TPAP gap described in README.md has closed just because
you restored the official package. After restoring it, go to
**Settings → Devices & services → + Add integration**, search for
**"TP-Link Smart Home"**, and try adding the H100 hub. If it fails with the
same `Unsupported device ... encrypt_scheme ... TPAP` error as before,
official support still isn't there yet — keep using this integration (or
reinstall it) rather than ending up with neither working.

### 2. Note down the current (`tapo_hub`) entity IDs

Same idea as the forward migration, in reverse: before removing anything,
record the `tapo_hub` entity IDs you want history to continue under
(Settings → Devices & services → Entities, filtered by integration "Tapo
Hub (H100)").

| Current entity_id (under `tapo_hub`)           | New entity_id (under `tplink`, once added)     |
|-----------------------------------------------|-----------------------------------------------|
| `sensor.<tapo_hub_temp_sensor_entity_id>`      | `sensor.<tplink_temp_sensor_entity_id>`        |
| `sensor.<tapo_hub_humidity_sensor_entity_id>`  | `sensor.<tplink_humidity_sensor_entity_id>`    |
| `binary_sensor.<tapo_hub_battery_entity_id>`   | `binary_sensor.<tplink_battery_entity_id>`     |
| `sensor.<tapo_hub_rssi_entity_id>`             | `sensor.<tplink_rssi_entity_id>`               |

### 3. Set up `tplink` for the device, then remove `tapo_hub`

1. Add the H100 under the official `tplink` integration and confirm it
   works with live data.
2. Remove this integration's config entries (Settings → Devices & services
   → the **Tapo Hub (H100)** entries → ⋮ → **Delete**). This frees up the
   old `tapo_hub` entity IDs.
3. Only then uninstall the integration files — see
   [README.md § Removing this integration](README.md#removing-this-integration-full-rollback)
   for that part.

### 4. Reuse the freed entity IDs where a compatible replacement exists

For each row you noted in step 2, if `tplink` created a *compatible*
replacement entity (same measurement, same device), go to **Settings →
Devices & services → Entities**, open the new `tplink` entity, and rename
its entity ID to the old `tapo_hub` one. As with the forward migration,
Home Assistant's statistics are keyed by `entity_id`, so the graph
continues instead of resetting — but only when the replacement entity is
genuinely equivalent; don't force an entity ID onto an entity measuring
something different just to keep a graph continuous.

If `tplink` doesn't expose an equivalent entity for something this
integration had (e.g. a feature not surfaced by the official integration),
there's nothing to rename it to — that statistic series simply stops
getting new data, same as any other removed entity.

### 5. Check dashboards and automations

Search your dashboards and automations for the old `tapo_hub.*` entity IDs
and update anything that wasn't automatically covered by the rename in
step 4 (automations that reference an entity_id directly are **not**
automatically updated by renaming — only the entity registry and
statistics are).

### What "migrating back" does and doesn't give you

- Renaming entity IDs keeps **existing** statistics/history attached to the
  new entity going forward; it does not retroactively merge two already-
  separate statistics series, and there's no supported way to splice them
  together after the fact.
- Logbook entries, the device registry record, and config entry history
  referencing `tapo_hub` are not erased just because you removed the
  integration — only the live entities and their future data move to
  `tplink`.
- This procedure does not guarantee you end up in exactly the state you'd
  be in if this integration had never been installed — see
  [README.md § What this does and doesn't undo](README.md#what-this-does-and-doesnt-undo)
  for what is and isn't reverted.
