# Multi Emulator Discord RPC

Discord Rich Presence for emulators (PPSSPP, Minecraft Bedrock) on Linux.

- **PPSSPP**: the game name and icon are read automatically from the window title (internal serial like `ULESxxxxx`), so switching games inside PPSSPP updates instantly
- **Minecraft Bedrock**: the launcher version is parsed from the `-dg` argument

## Install

```bash
./install.sh
```

The script creates a venv plus a systemd user service (`mcpe-discord-rpc.service`) and enables it.

## Configuration

Create `config.json` (not committed):

```json
{
    "client_id": "DISCORD_APPLICATION_ID",
    "poll_interval": 5
}
```

`client_id` = the Application ID of your app from the [Discord Developer Portal](https://discord.com/developers/applications).

## Rich Presence assets

Game icons are Discord assets, not files the script reads from disk. They live in the [Discord Developer Portal](https://discord.com/developers/applications) — open your app > **Rich Presence** > **Art Assets** > **Add Image(s)**, and upload each game's cover art with an asset name that matches (lowercase, no spaces).

Asset names must exactly match the values in the `ICONS` dict (`main.py`). Local copies of all icons live in the `icons/` folder, with file names equal to the portal asset names:

| File in `icons/` | Portal asset name |
|---|---|
| `persona3p.jpg` | `persona3p` |
| `batman.jpg` | `batman` |
| `lumines.jpg` | `lumines` |
| `locoroco.jpg` | `locoroco` |
| `fifa14.jpg` | `fifa14` |
| `toystory3.jpg` | `toystory3` |
| `everybodysgolf.jpg` | `everybodysgolf` |
| `crashtitans.jpg` | `crashtitans` |
| `dantesinferno.jpg` | `dantesinferno` |
| `halfminutehero.jpg` | `halfminutehero` |
| `minecraft.png` | `minecraft` |
| `ppsspp.jpg` | `ppsspp` |

## Adding a new PPSSPP game

1. Open the game once in PPSSPP
2. Read the serial from the logs: `journalctl --user -u mcpe-discord-rpc.service -f` (the `[DEBUG] window title` line)
3. Add `"<SERIAL>": "<asset-key>"` to the `ICONS` dict in `main.py`
4. Need a shorter display name? Add it to `SHORT_NAMES`

## Logs

```bash
journalctl --user -u mcpe-discord-rpc.service -f
```
