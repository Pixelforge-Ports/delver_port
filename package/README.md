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

Controls use Delver's native Xbox 360 gamepad layout. The left stick moves and
the right stick looks; use the in-game gamepad options to view or change bindings.
Menu prompts use Xbox button names. **B** jumps during gameplay and goes back
in menus. Select + Start exits through PortMaster.
Two analog sticks are recommended for movement and looking.

The supplied `delver/options.txt` is copied to `delver/save/options.txt` only on
first launch, preserving existing settings and gamepad bindings.
