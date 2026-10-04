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

## Installation

1. Update PortMaster. Put **delver.zip** in PortMaster's `autoinstall/` directory, then open PortMaster to install it. Connect to the network to download Java 17 and Westonpack if they are not installed yet.
2. Copy the owned file to **`<ports directory>/delver/gamedata/delver.jar`**.
3. Launch **Delver** from your firmware's ports menu.

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

## Build the PortMaster package

Requires Python 3.9+ and JDK 17 or newer. **No purchased JAR or DAT is required to compile
the host or build the ZIP.** From this source directory, on Windows:

```bat
python tools/build.py --jdk "C:\Program Files\Java\jdk-17"
```

Replace the quoted path with your installed JDK directory, for example `jdk-26.0.2.1`.
Use double quotes in Windows Command Prompt. On Linux:

```sh
python3 tools/build.py --jdk "/path/to/installed/jdk-17"
```

The first build downloads checksum-pinned public dependencies. Later builds may add
`--offline` to use the cache. Only `org/portmaster/delver/` host classes go into
`delver-host.jar`; public runtime libraries are prepared separately under `build/artifacts/`.

The only release artifact is **`dist/delver.zip`**, a universal BYO-data ZIP.
The build also prepares **`ports/delver/`** in the PortMaster source submission layout.
It never packages the owned game archive, Windows runtimes or personal saves.
Each full build compiles a fresh host under `build/artifacts/`; `package/` files remain unchanged.
The ZIP keeps `README.md` as supplied. Delver runtime libraries are rebuilt from pinned public dependencies.
After editing package documentation or controls, rebuild with:

```sh
python tools/build.py --package-only
python tools/verify_package.py
```

`--package-only` requires a previously built host. The optional `--game-jar` argument checks
a supplied archive's fingerprint; it does not participate in compilation. Downloading a
public compile dependency does not supply the commercial game. Copy the owned files after installing.

Run `bash tests/verify_display.sh` for display-helper checks. Run `python tests/verify_launcher.py` for lifecycle checks. These tests use
mock runtimes and do not mount or run games. See `testing_thread.txt` for the Discord testing post. Upload source files using Git;
`build/`, `dist/`, generated `ports/` and owned data are excluded by `.gitignore`.

The Discord draft stays in source `testing_thread.txt`; it is not installed by the ZIP.
