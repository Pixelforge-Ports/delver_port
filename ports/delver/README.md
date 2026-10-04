## Notes

Thanks to [Priority Interrupt](https://store.steampowered.com/app/249630/Delver/) for creating **Delver**. Explore shifting dungeons in a first-person roguelike filled with monsters, loot and secrets. PortMaster adaptation by **Pixelforge Ports (Ronax)**.

## Get delver.jar from Steam

Windows / Linux:

1. Own [Delver on Steam](https://store.steampowered.com/app/249630/Delver/) and sign into the Steam desktop client.
2. Open `steam://open/console`. On Windows, press Windows + R, enter that address and press Enter. On Linux, open that address with Steam.
3. Download **Delver v1.08, Windows depot 249631, manifest 6680730644186394716** using Steam's Console tab:

```text
download_depot 249630 249631 6680730644186394716
```

4. Open the directory reported by Steam, usually `<Steam>/steamapps/content/app_249630/depot_249631/`, and find `delver.jar` (**69,330,539 bytes**).

Supported archive SHA-256 (`delver.jar`):

```text
a2d58e87b09f588ff8389508e43accf7d3c6ce949b5aa4d31d6380574ec095ae
```

Copy the owned file to **`<ports directory>/delver/gamedata/delver.jar`**.
Launch **Delver** from your firmware's ports menu.

The launcher detects display size and supports **640x480**, **720x480**, **720x720**, **1024x768**, **1280x720**, and other valid PortMaster dimensions while preserving aspect ratio. If detection is wrong, put the actual size, such as `720x480`, in `delver/resolution.txt`; use `auto` or remove the file to restore automatic detection.

Back up **`delver/save/`** before updating. If startup fails, check **`delver/log.txt`**. When reporting a problem, include the device, firmware version, resolution, reproduction steps, and log. Keep purchased game files private.

## Controls

| Button | Action |
| --- | --- |
| Left stick / D-pad | Move forward/backward and strafe (WASD) |
| Right stick | Look / move menu cursor |
| A | Use / interact (E) |
| B | Jump (Space) |
| X | Inventory (I) |
| Y | Map (M) |
| L1 / R1 | Previous / next item |
| L2 | Drop item (Q) |
| R2 | Attack / click menu or inventory item (left mouse) |
| R3 (hold) | Slower mouse movement |
| Start | Pause / options / back (Escape) |
| Select (hold) + A | Enter / confirm |
| Select (hold) + B | Escape / back |
| Select (hold) + D-pad | Arrow keys |
| Select + Start | PortMaster exit shortcut |

Use the right stick to point and **R2** to click menu or inventory items.
**Select + A** sends Enter. **B** jumps, **L2** drops an item and **R2** attacks.
The supplied `delver/options.txt` sets jump to Space and mouse X/Y sensitivity to `3`.
It is copied to `delver/save/options.txt` only on first launch, preserving existing settings.
Two analog sticks are recommended for movement and looking.
