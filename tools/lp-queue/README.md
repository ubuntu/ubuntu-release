# LP Queue TUI

A small standalone TUI tool for working with the Ubuntu Launchpad upload queue.

## Features

- **List** all items in the upload queue for a given Ubuntu series
- **Review** packages by viewing the debdiff between the current archive version and the new upload
- **Accept** packages into the archive
- **Reject** packages with a comment explaining the reason

## Installation

```bash
sudo apt install python3-launchpadlib python3-textual
sudo apt install --no-install-recommends diffoscope-minimal
ln -s "$(realpath lp-queue)" ~/.local/bin/lp-queue
```
or
```bash
pip install .
```

For development:

```bash
pip install -e ".[dev]"
```

## Usage

Run the TUI:

```bash
lp-queue
```

Or as a Python module:

```bash
python -m lp_queue
```

## Keybindings

| Key  | Action                              |
|------|-------------------------------------|
| `r`  | Review selected package (debdiff)   |
| `a`  | Accept selected package             |
| `j`  | Reject selected package (with comment) |
| `F5` | Refresh the queue listing           |
| `q`  | Quit the application                |

## Requirements

- Python 3.10+
- `launchpadlib` for Launchpad API access
- `textual` for the terminal UI framework
- Ubuntu archive access credentials (obtained via Launchpad OAuth)

## How It Works

1. On startup, the tool authenticates with Launchpad using `launchpadlib`
2. It fetches the current upload queue for the configured Ubuntu series
3. Items are displayed in a table with package name, version, component, etc.
4. You can review, accept, or reject packages using the keybindings above

For syncs from Debian, the review shows the debdiff comparing the Debian
version against what is currently in the Ubuntu archive. You can also visit
the Debian tracker at `https://tracker.debian.org/pkg/<package-name>` for
additional context.
