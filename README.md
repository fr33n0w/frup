# Fast Reticulum Updater (FRUP) v1.0

## 🆕 What's New in v1.0

### System Detection & Smart Package Management

FRUP now automatically detects your system environment and intelligently handles package compatibility:

- **Automatic System Detection**: Identifies your OS, architecture, desktop environment, and special environments (Termux, Raspbian, SSH sessions)
- **Desktop Environment Detection**: Checks for X11, Wayland, and other desktop indicators
- **Smart Package Skipping**: Automatically skips desktop-only packages (like Sideband) on headless systems
- **System Info Display**: Shows detailed system information before running update checks

### Supported Environments

FRUP correctly identifies and handles:
- 🖥️ **Desktop Systems**: Full package support including Sideband
- 🤖 **Termux (Android)**: Automatically skips desktop-only packages
- 🥧 **Raspberry Pi OS**: Detects headless vs desktop configurations
- 🖧 **SSH/Server**: Recognizes remote sessions without desktop
- 🐧 **Headless Linux**: Works on servers and minimal installations

### Example Output

```
** System Information **
  Debian GNU/Linux 12 (bookworm) | x86_64 | Headless/Server | Python 3.11.2
  ℹ No desktop environment detected
  ℹ Desktop-only packages (like Sideband) will be skipped
```

### Configuration

Desktop-only packages are marked with `requires_desktop: true` in the configuration:

```json
{
  "name": "sideband",
  "display_name": "Sideband",
  "pypi_name": "sbapp",
  "requires_desktop": true
}
```

---

# 🎉 FRUP v0.9 Update - PyPI-First Approach!

> **Important Update (January 2026):** FRUP has been updated to check PyPI instead of GitHub for package versions. This makes version checking faster, more reliable, and aligns with how Reticulum packages are now being released.

## What's New in v0.9

### 🚀 Major Changes

- **PyPI-First Checking**: Now checks PyPI.org directly for package versions (much faster!)
- **GitHub Fallback**: Only uses GitHub for packages not available on PyPI
- **New Packages Added**: 
  - ✨ **LXST** - Reticulum Audio Protocol  
  - ✨ **Columba** - Android-based LXMF client
- **Fixed Sideband**: Now uses correct PyPI package name (`sbapp`)

### 📦 Updated Package List

**Automatically Updatable (PyPI):**
- RNS, LXMF, LXST, NomadNet, Sideband

**Information Only (GitHub - Manual Install):**
- MeshChat, Columba, RNode, RNode CE, RNode TN

### ⚡ Why This Update?

Mark Qvist (Reticulum's author) now publishes releases primarily to PyPI rather than GitHub. This means:
- ✅ Faster version checks (no GitHub API rate limits)
- ✅ More reliable (PyPI has higher uptime)
- ✅ Matches official release process
- ✅ No need for GitHub tokens

### 🔄 Migration Notes

If you have a custom `frup_config.json`, you'll need to update it to use the new format:

**Old format:**
```json
{
  "name": "Sideband",
  "url": "https://github.com/markqvist/Sideband"
}
```

**New format:**
```json
{
  "name": "sideband",
  "display_name": "Sideband",
  "pypi_name": "sbapp",
  "url": "https://github.com/markqvist/Sideband"
}
```

Generate a new example config with:
```bash
python3 frup.py --save-config
```

---

# Fast Reticulum Updater (F.R.U.) v0.8

A Python tool to check and update Reticulum ecosystem packages.

## New Features in v0.8

Minor fix: Fixed display typo "updateing" bug

### 🚀 Performance
- **Single API call per package** - Caches GitHub version checks
- **Timeouts** on all network and subprocess operations
- **Efficient version checking** with normalized comparison

### 🎨 User Experience  
- **Colored output** (automatic, with fallback if colorama not installed)
- **Progress indicators** (✓ ✗ ⚠ − ℹ)
- **Config status display** - Shows whether using default or custom config
- **Summary report** showing updated, skipped, and failed packages
- **Clear status messages** throughout the process

### ⚙️ Command Line Arguments
- `--auto` / `-a` : Automatically update all packages without prompting
- `--check-only` / `-c` : Only check versions without updating
- `--quiet` / `-q` : Minimal output (errors and summary only)
- `--break-system-packages` / `-b` : Use --break-system-packages flag for pip (required on some systems)
- `--save-config` : Generate example configuration file
- `--version` / `-v` : Show version information
- `--help` / `-h` : Show help message

### 📁 Configuration Files
Supports custom package lists via JSON configuration. Checks for config in:
1. `frup_config.json` (current directory)
2. `.frup_config.json` (hidden file in current directory)  
3. `~/.frup_config.json` (user home directory)

When starting, the script shows whether it's using default or custom configuration.

### 🛡️ Error Handling
- Network timeouts (10 seconds for API calls)
- Process timeouts (120 seconds for pip operations)
- Graceful failure handling with clear error messages
- Keyboard interrupt handling (Ctrl+C)

## Installation

### Requirements
- Python 3.6+
- pip
- requests library (`pip install requests`)
- colorama library (optional, for colored output: `pip install colorama`)

### Setup
```bash
# Make executable (optional)
chmod +x frup.py

# Install optional colorama for colored output
pip install colorama
```

## Usage Examples

### Interactive Mode (default)
```bash
python3 frup.py
```
Shows all information and prompts for each update.

### Auto-Update All Packages
```bash
python3 frup.py --auto
```
Automatically updates all out-of-date packages without prompting.

### For Systems Requiring --break-system-packages (Debian 12+, Ubuntu 23.04+)
```bash
# Interactive with system packages flag
python3 frup.py --break-system-packages

# Auto-update with system packages flag
python3 frup.py --break-system-packages --auto

# Short form
python3 frup.py -b -a
```

### Check Only (no updates)
```bash
python3 frup.py --check-only
```
Shows version comparison without performing any updates.

### Quiet Auto-Update
```bash
python3 frup.py --quiet --auto
```
Silently updates all packages, showing only the summary.

### Generate Config File
```bash
python3 frup.py --save-config
```
Creates `frup_config_example.json` that you can customize and rename to `frup_config.json`.

## Configuration File Format

Create a `frup_config.json` file to customize which packages to check:

```json
{
  "packages": [
    {
      "name": "RNS",
      "url": "https://github.com/markqvist/Reticulum"
    },
    {
      "name": "CustomPackage",
      "url": "https://github.com/user/repo",
      "manual_install": true,
      "skip_local_check": false
    }
  ]
}
```

### Package Options
- `name`: Package name (used for pip)
- `url`: GitHub repository URL
- `manual_install`: If true, only shows available version
- `skip_local_check`: Skip checking local installation
- `skip_version_comparison`: Skip version comparison
- `online_only`: Only check GitHub version

## Output Symbols

- ✓ Success / Up to date
- ✗ Error / Failed
- ⚠ Warning / Timeout
- − Not installed / Skipped
- ℹ Information

## Status Messages

When starting, the script displays which configuration it's using:
- `Using default configuration` - No config file found, using built-in packages
- `Using custom config: [path]` - Found and loaded custom configuration

## Version History

- **v0.8** - Minor fix of "updateing" display typo bug
- **v0.7** - Major rewrite with CLI args, config files, colored output, better error handling
- **v0.6** - Fixed Linux keyboard permission issue
- **v0.5** - Initial version

## Author

Created by F

## License

Open source - feel free to modify and distribute

## Troubleshooting

### "externally-managed-environment" error?
Modern systems (Debian 12+, Ubuntu 23.04+, etc.) require the `--break-system-packages` flag:
```bash
python3 frup.py --break-system-packages --auto
# or short form
python3 frup.py -b -a
```
The script will automatically detect this and prompt you to retry with the flag if needed.

### No colored output?
Install colorama: `pip install colorama`

### Permission errors?
No longer requires sudo! The keyboard dependency was removed in v0.6+

### Network timeouts?
The tool has a 10-second timeout for GitHub API calls. Check your internet connection.

### Custom packages not updating?
Make sure the package name matches exactly what's used in pip.

### Want to reset to default packages?
Simply delete or rename your `frup_config.json` file.
