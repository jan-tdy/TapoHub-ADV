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
