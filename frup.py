#!/usr/bin/env python3
"""
Fast Reticulum Updater v1.0
Author: F
Improvements: PyPI-first approach, efficiency, error handling, CLI arguments, colored output, summary, system detection
"""

import requests
import subprocess
import sys
import argparse
import json
import os
import platform
from typing import Dict, List, Optional

# Try to import colorama for colored output
try:
    from colorama import init, Fore, Style
    init()
    GREEN = Fore.GREEN
    RED = Fore.RED
    YELLOW = Fore.YELLOW
    CYAN = Fore.CYAN
    RESET = Style.RESET_ALL
    BRIGHT = Style.BRIGHT
except ImportError:
    # Fallback if colorama not installed
    GREEN = RED = YELLOW = CYAN = RESET = BRIGHT = ""

class SystemDetector:
    """Detect system information and capabilities"""
    
    def __init__(self):
        self.os_type = platform.system()
        self.os_release = platform.release()
        self.machine = platform.machine()
        self.is_termux = self.detect_termux()
        self.is_raspbian = self.detect_raspbian()
        self.is_pi_zero = self.detect_pi_zero()
        self.has_desktop = self.detect_desktop_environment()
        self.python_version = platform.python_version()
        self.is_slow_system = self.detect_slow_system()
        
    def detect_termux(self) -> bool:
        """Detect if running on Termux (Android)"""
        return os.path.exists('/data/data/com.termux') or 'com.termux' in os.environ.get('PREFIX', '')
    
    def detect_raspbian(self) -> bool:
        """Detect if running on Raspbian/Raspberry Pi OS"""
        try:
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    content = f.read().lower()
                    return 'raspbian' in content or 'raspberry' in content
        except:
            pass
        return False
    
    def detect_pi_zero(self) -> bool:
        """Detect if running on Raspberry Pi Zero (very slow single-core)"""
        try:
            # Check /proc/cpuinfo for Pi Zero identifiers
            if os.path.exists('/proc/cpuinfo'):
                with open('/proc/cpuinfo', 'r') as f:
                    content = f.read().lower()
                    # Pi Zero has BCM2835 and single core
                    if 'bcm2835' in content or 'bcm2708' in content:
                        # Check if single core
                        if content.count('processor') == 1:
                            return True
            # Check device model
            if os.path.exists('/proc/device-tree/model'):
                with open('/proc/device-tree/model', 'r') as f:
                    model = f.read().lower()
                    if 'pi zero' in model or 'pi 1' in model:
                        return True
        except:
            pass
        return False
    
    def detect_slow_system(self) -> bool:
        """Detect if system is likely to be slow (single-core, low-power)"""
        # Pi Zero is definitely slow
        if self.is_pi_zero:
            return True
        
        # Check CPU count
        try:
            import multiprocessing
            cpu_count = multiprocessing.cpu_count()
            if cpu_count == 1:
                return True
        except:
            pass
        
        # Termux on older Android devices can be slow
        if self.is_termux:
            return True
        
        return False
    
    def detect_desktop_environment(self) -> bool:
        """Detect if a desktop environment is available"""
        # Check for Termux (no desktop)
        if self.is_termux:
            return False
        
        # Check common desktop environment variables
        desktop_vars = ['DISPLAY', 'WAYLAND_DISPLAY', 'XDG_CURRENT_DESKTOP', 'DESKTOP_SESSION']
        if any(os.environ.get(var) for var in desktop_vars):
            return True
        
        # Check for X11 or Wayland
        if os.path.exists('/tmp/.X11-unix') or os.path.exists('/run/user'):
            return True
        
        # For Windows, assume desktop is available
        if self.os_type == 'Windows':
            return True
        
        # For macOS, assume desktop is available
        if self.os_type == 'Darwin':
            return True
        
        # Check if running in SSH session (likely headless)
        if os.environ.get('SSH_CONNECTION') or os.environ.get('SSH_CLIENT'):
            return False
        
        # Default to False for server/headless systems
        return False
    
    def get_system_description(self) -> str:
        """Get a human-readable system description"""
        parts = []
        
        # OS Type
        if self.is_termux:
            parts.append("Termux (Android)")
        elif self.is_pi_zero:
            parts.append("Raspberry Pi Zero")
        elif self.is_raspbian:
            parts.append("Raspberry Pi OS")
        elif self.os_type == 'Linux':
            # Try to get distribution name
            try:
                if os.path.exists('/etc/os-release'):
                    with open('/etc/os-release', 'r') as f:
                        for line in f:
                            if line.startswith('PRETTY_NAME='):
                                distro = line.split('=')[1].strip().strip('"')
                                parts.append(distro)
                                break
                        else:
                            parts.append(f"Linux {self.os_release}")
                else:
                    parts.append(f"Linux {self.os_release}")
            except:
                parts.append(f"Linux {self.os_release}")
        else:
            parts.append(f"{self.os_type} {self.os_release}")
        
        # Architecture
        parts.append(self.machine)
        
        # Desktop status
        if self.has_desktop:
            parts.append("Desktop")
        else:
            parts.append("Headless/Server")
        
        # Python version
        parts.append(f"Python {self.python_version}")
        
        return " | ".join(parts)
    
    def should_skip_desktop_packages(self) -> bool:
        """Determine if desktop-only packages should be skipped"""
        return not self.has_desktop

class ReticulumUpdater:
    def __init__(self, auto_update=False, quiet=False, check_only=False, break_system=False):
        self.auto_update = auto_update
        self.quiet = quiet
        self.check_only = check_only
        self.break_system = break_system
        self.online_versions = {}
        self.local_versions = {}
        self.updated = []
        self.skipped = []
        self.failed = []
        self.already_updated = []
        self.using_custom_config = False
        self.config_path = None
        self.needs_break_system = False
        
        # Detect system
        self.system = SystemDetector()
        
        # Default packages - can be overridden by config file
        # NOTE: PyPI package names are used for pip installation
        self.packages = [
            # Protocol Stack - PyPI packages
            {'name': 'rns', 'display_name': 'RNS', 'pypi_name': 'rns', 
             'url': 'https://github.com/markqvist/Reticulum'},
            {'name': 'lxmf', 'display_name': 'LXMF', 'pypi_name': 'lxmf', 
             'url': 'https://github.com/markqvist/lxmf'},
            {'name': 'lxst', 'display_name': 'LXST', 'pypi_name': 'lxst', 
             'url': 'https://github.com/markqvist/lxst'},
            
            # Software - PyPI packages
            {'name': 'nomadnet', 'display_name': 'NomadNet', 'pypi_name': 'nomadnet', 
             'url': 'https://github.com/markqvist/nomadnet'},
            {'name': 'sideband', 'display_name': 'Sideband', 'pypi_name': 'sbapp', 
             'url': 'https://github.com/markqvist/Sideband',
             'requires_desktop': True},  # Mark as desktop-only
            
            # Software - GitHub only (manual install)
            {'name': 'meshchat', 'display_name': 'MeshChat', 'pypi_name': None,
             'url': 'https://github.com/liamcottle/reticulum-meshchat',
             'manual_install': True, 'skip_local_check': True, 'skip_version_comparison': True, 
             'online_only': True},
            {'name': 'columba', 'display_name': 'Columba', 'pypi_name': None,
             'url': 'https://github.com/torlando-tech/columba',
             'manual_install': True, 'skip_local_check': True, 'skip_version_comparison': True, 
             'online_only': True},
            
            # LoRa Firmware - GitHub only (manual install)
            {'name': 'rnode', 'display_name': 'RNode', 'pypi_name': None,
             'url': 'https://github.com/markqvist/RNode_Firmware',
             'manual_install': True, 'skip_local_check': True, 'skip_version_comparison': True, 
             'online_only': True},
            {'name': 'rnode_ce', 'display_name': 'RNode CE', 'pypi_name': None,
             'url': 'https://github.com/liberatedsystems/RNode_Firmware_CE',
             'manual_install': True, 'skip_local_check': True, 'skip_version_comparison': True, 
             'online_only': True},
            {'name': 'rnode_tn', 'display_name': 'RNode TN', 'pypi_name': None,
             'url': 'https://github.com/attermann/microReticulum_Firmware',
             'manual_install': True, 'skip_local_check': True, 'skip_version_comparison': True, 
             'online_only': True}
        ]
        
        # Load custom config if available
        self.load_config()
    
    def load_config(self):
        """Load configuration from file if it exists"""
        config_files = ['frup_config.json', '.frup_config.json', '~/.frup_config.json']
        for config_file in config_files:
            config_path = os.path.expanduser(config_file)
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        if 'packages' in config:
                            self.packages = config['packages']
                            self.using_custom_config = True
                            self.config_path = config_path
                        break
                except Exception as e:
                    print(f"{RED}Error loading config from {config_path}: {e}{RESET}")
                    print(f"{YELLOW}Using default configuration instead{RESET}")
    
    def save_example_config(self):
        """Save an example configuration file"""
        example_config = {
            "comment": "Fast Reticulum Updater Configuration - Customize packages to check/update",
            "packages": [
                {
                    "name": "rns",
                    "display_name": "RNS",
                    "pypi_name": "rns",
                    "url": "https://github.com/markqvist/Reticulum"
                },
                {
                    "name": "lxmf",
                    "display_name": "LXMF",
                    "pypi_name": "lxmf",
                    "url": "https://github.com/markqvist/lxmf"
                },
                {
                    "name": "lxst",
                    "display_name": "LXST",
                    "pypi_name": "lxst",
                    "url": "https://github.com/markqvist/lxst"
                },
                {
                    "name": "nomadnet",
                    "display_name": "NomadNet",
                    "pypi_name": "nomadnet",
                    "url": "https://github.com/markqvist/nomadnet"
                },
                {
                    "name": "sideband",
                    "display_name": "Sideband",
                    "pypi_name": "sbapp",
                    "url": "https://github.com/markqvist/Sideband",
                    "requires_desktop": true,
                    "comment": "PyPI package name is 'sbapp', requires desktop environment"
                },
                {
                    "name": "meshchat",
                    "display_name": "MeshChat",
                    "pypi_name": null,
                    "url": "https://github.com/liamcottle/reticulum-meshchat",
                    "manual_install": true,
                    "skip_local_check": true,
                    "skip_version_comparison": true,
                    "online_only": true
                },
                {
                    "name": "columba",
                    "display_name": "Columba",
                    "pypi_name": null,
                    "url": "https://github.com/torlando-tech/columba",
                    "manual_install": true,
                    "skip_local_check": true,
                    "skip_version_comparison": true,
                    "online_only": true
                },
                {
                    "name": "rnode",
                    "display_name": "RNode",
                    "pypi_name": null,
                    "url": "https://github.com/markqvist/RNode_Firmware",
                    "manual_install": true,
                    "skip_local_check": true,
                    "skip_version_comparison": true,
                    "online_only": true
                },
                {
                    "name": "rnode_ce",
                    "display_name": "RNode CE",
                    "pypi_name": null,
                    "url": "https://github.com/liberatedsystems/RNode_Firmware_CE",
                    "manual_install": true,
                    "skip_local_check": true,
                    "skip_version_comparison": true,
                    "online_only": true
                },
                {
                    "name": "rnode_tn",
                    "display_name": "RNode TN",
                    "pypi_name": null,
                    "url": "https://github.com/attermann/microReticulum_Firmware",
                    "manual_install": true,
                    "skip_local_check": true,
                    "skip_version_comparison": true,
                    "online_only": true
                }
            ],
            "notes": [
                "pypi_name: The package name on PyPI (for pip install)",
                "name: Internal identifier (lowercase, no spaces)",
                "display_name: Human-readable name shown to user",
                "manual_install: true = Cannot be installed via pip",
                "online_only: true = Only check online version, don't show in updates",
                "requires_desktop: true = Only install on systems with desktop environment",
                "Set pypi_name to null for GitHub-only packages"
            ]
        }
        with open('frup_config_example.json', 'w') as f:
            json.dump(example_config, f, indent=2)
        print(f"{GREEN}Example config saved to: frup_config_example.json{RESET}")
        print(f"{CYAN}Rename to 'frup_config.json' to use it{RESET}")
    
    def normalize_version(self, version: Optional[str]) -> Optional[str]:
        """Remove common prefixes from version strings for comparison"""
        if version:
            return version.lstrip('v').lstrip('V').strip()
        return version
    
    def print_header(self):
        """Print the application header"""
        if not self.quiet:
            print()
            print(f"{BRIGHT}=============================================={RESET}")
            print(f"{BRIGHT}      Fast Reticulum Updater v1.0 by F{RESET}")
            print(f"{BRIGHT}      Now with System Detection!{RESET}")
            print(f"{BRIGHT}=============================================={RESET}")
            
            # Show system information
            print(f"\n{BRIGHT}** System Information **{RESET}")
            system_desc = self.system.get_system_description()
            print(f"  {CYAN}{system_desc}{RESET}")
            
            # Warn about slow systems
            if self.system.is_slow_system:
                print(f"  {YELLOW}⚠ Slow system detected - package installs may take longer{RESET}")
                if self.system.is_pi_zero:
                    print(f"  {YELLOW}⚠ Pi Zero detected - using extended timeout (5 minutes){RESET}")
            
            # Warn about desktop-only packages if no desktop detected
            if self.system.should_skip_desktop_packages():
                print(f"  {YELLOW}ℹ No desktop environment detected{RESET}")
                print(f"  {YELLOW}ℹ Desktop-only packages (like Sideband) will be skipped{RESET}")
            
            # Show config status
            if self.using_custom_config:
                print(f"\n{CYAN}Using custom config: {self.config_path}{RESET}")
            else:
                print(f"\n{CYAN}Using default configuration{RESET}")
    
    def fetch_pypi_version(self, package_name: str) -> Optional[str]:
        """Fetch version from PyPI"""
        try:
            response = requests.get(
                f"https://pypi.org/pypi/{package_name}/json",
                timeout=10
            )
            response.raise_for_status()
            version = response.json()['info']['version']
            return version
        except requests.exceptions.RequestException:
            return None
    
    def fetch_github_version(self, repo_url: str) -> Optional[str]:
        """Fetch version from GitHub releases"""
        try:
            repo_parts = repo_url.split('/')
            repo = f"{repo_parts[-2]}/{repo_parts[-1]}"
            
            response = requests.get(
                f"https://api.github.com/repos/{repo}/releases/latest",
                timeout=10,
                headers={'Accept': 'application/vnd.github.v3+json'}
            )
            response.raise_for_status()
            version = response.json().get("tag_name", "Unknown")
            return version
        except requests.exceptions.RequestException:
            return None
    
    def should_skip_package(self, package: dict) -> bool:
        """Determine if a package should be skipped based on system requirements"""
        # Check if package requires desktop
        if package.get('requires_desktop') and self.system.should_skip_desktop_packages():
            return True
        return False
    
    def get_install_timeout(self) -> int:
        """Get appropriate timeout for pip install based on system speed"""
        if self.system.is_pi_zero:
            return 300  # 5 minutes for Pi Zero
        elif self.system.is_slow_system:
            return 240  # 4 minutes for other slow systems
        else:
            return 120  # 2 minutes for normal systems
    
    def fetch_online_versions(self):
        """Fetch all online versions (PyPI first, then GitHub)"""
        if not self.quiet:
            print(f"\n{BRIGHT}** Fetching Latest Versions **{RESET}")
        
        for package in self.packages:
            display_name = package.get('display_name', package['name'])
            
            # Skip if system requirements not met
            if self.should_skip_package(package):
                if not self.quiet and not package.get('online_only'):
                    print(f"  {YELLOW}−{RESET} {display_name}: Skipped (requires desktop)")
                continue
            
            # Try PyPI first if pypi_name is specified
            if package.get('pypi_name'):
                version = self.fetch_pypi_version(package['pypi_name'])
                source = "PyPI"
            else:
                # Fallback to GitHub for packages not on PyPI
                version = self.fetch_github_version(package['url'])
                source = "GitHub"
            
            self.online_versions[package['name']] = version
            
            if not self.quiet:
                if version:
                    print(f"  {GREEN}✓{RESET} {display_name}: {CYAN}{version}{RESET} ({source})")
                else:
                    print(f"  {YELLOW}⚠{RESET} {display_name}: Failed to fetch from {source}")
    
    def check_local_versions(self):
        """Check locally installed versions"""
        if not self.quiet:
            print(f"\n{BRIGHT}** Local Installed Versions **{RESET}")
        
        for package in self.packages:
            display_name = package.get('display_name', package['name'])
            
            # Skip if system requirements not met
            if self.should_skip_package(package):
                self.local_versions[package['name']] = None
                continue
            
            # Skip packages marked as online_only or skip_local_check
            if package.get('skip_local_check') or package.get('online_only'):
                self.local_versions[package['name']] = None
                if not self.quiet and not package.get('online_only'):
                    print(f"  {YELLOW}−{RESET} {display_name}: Skipped")
                continue
            
            # Use pypi_name for pip show if available, otherwise use name
            pip_package_name = package.get('pypi_name') or package['name']
            
            try:
                result = subprocess.run(
                    ["pip", "show", pip_package_name], 
                    capture_output=True, 
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        if "Version:" in line:
                            version = line.split(":")[1].strip()
                            self.local_versions[package['name']] = version
                            if not self.quiet:
                                print(f"  {GREEN}✓{RESET} {display_name}: {CYAN}{version}{RESET}")
                            break
                else:
                    self.local_versions[package['name']] = None
                    if not self.quiet:
                        print(f"  {YELLOW}−{RESET} {display_name}: Not installed")
            
            except subprocess.TimeoutExpired:
                self.local_versions[package['name']] = None
                if not self.quiet:
                    print(f"  {YELLOW}⚠{RESET} {display_name}: Check timeout")
            
            except Exception as e:
                self.local_versions[package['name']] = None
                if not self.quiet:
                    print(f"  {RED}✗{RESET} {display_name}: Error checking")
    
    def compare_and_update(self):
        """Compare versions and optionally update packages"""
        if self.check_only:
            print(f"\n{BRIGHT}** Version Comparison (Check Only Mode) **{RESET}")
        else:
            print(f"\n{BRIGHT}** Version Comparison & Update **{RESET}")
        
        for package in self.packages:
            # Skip if system requirements not met
            if self.should_skip_package(package):
                continue
            
            # Skip certain packages
            if package.get('skip_version_comparison') or package.get('online_only'):
                continue
            
            name = package['name']
            display_name = package.get('display_name', name)
            online_version = self.online_versions.get(name)
            local_version = self.local_versions.get(name)
            
            # Normalize versions for comparison
            norm_online = self.normalize_version(online_version)
            norm_local = self.normalize_version(local_version)
            
            print(f"\n{BRIGHT}{display_name}:{RESET}")
            
            # Check if versions could be retrieved
            if online_version is None:
                print(f"  {RED}Cannot compare - Online version unavailable{RESET}")
                self.failed.append(display_name)
                continue
            
            # Compare versions
            if local_version is None:
                print(f"  {YELLOW}Not installed{RESET} (Available: {CYAN}{online_version}{RESET})")
                action = "install"
                should_update = True
            elif norm_local == norm_online:
                print(f"  {GREEN}✓ Up to date!{RESET} ({CYAN}{local_version}{RESET})")
                self.already_updated.append(display_name)
                continue
            else:
                print(f"  {YELLOW}Update available:{RESET} {local_version} → {CYAN}{online_version}{RESET}")
                action = "update"
                should_update = True
            
            # Handle manual install packages
            if package.get('manual_install'):
                print(f"  {CYAN}ℹ Please {action} manually from: {package['url']}{RESET}")
                self.skipped.append(display_name)
                continue
            
            # Skip if check-only mode
            if self.check_only:
                continue
            
            # Handle updates
            if should_update:
                if self.auto_update:
                    response = 'y'
                    action_verb = "installing" if action == "install" else "updating"
                    print(f"  {CYAN}Auto-{action_verb}...{RESET}")
                else:
                    response = input(f"  Do you want to {action} {display_name}? (y/n): ").strip().lower()
                
                if response == 'y':
                    action_verb = "Installing" if action == "install" else "Updating"
                    print(f"  {CYAN}{action_verb} {display_name}...{RESET}")
                    
                    # Use pypi_name for pip install if available
                    pip_package_name = package.get('pypi_name') or package['name']
                    
                    # Get appropriate timeout for this system
                    install_timeout = self.get_install_timeout()
                    
                    # Prepare pip command
                    pip_cmd = ["pip", "install", "--upgrade", pip_package_name]
                    
                    # Try without --break-system-packages first
                    try:
                        result = subprocess.run(
                            pip_cmd,
                            capture_output=True,
                            text=True,
                            timeout=install_timeout
                        )
                        
                        # If failed due to externally-managed-environment, retry with flag
                        if result.returncode != 0 and "externally-managed-environment" in result.stderr:
                            if not self.quiet:
                                print(f"  {YELLOW}System requires --break-system-packages flag, retrying...{RESET}")
                            self.needs_break_system = True
                            
                            if self.break_system:
                                pip_cmd.append("--break-system-packages")
                            else:
                                # Ask user for permission if not already given
                                if not self.quiet:
                                    print(f"  {YELLOW}This system requires --break-system-packages flag.{RESET}")
                                    retry = input(f"  Retry with --break-system-packages? (y/n): ").strip().lower()
                                    if retry == 'y':
                                        pip_cmd.append("--break-system-packages")
                                    else:
                                        print(f"  {YELLOW}Skipped {display_name} (requires --break-system-packages){RESET}")
                                        self.skipped.append(display_name)
                                        continue
                                else:
                                    # In quiet mode with no permission, skip
                                    self.failed.append(display_name)
                                    continue
                            
                            # Retry with the flag and extended timeout for slow systems
                            if self.system.is_slow_system and not self.quiet:
                                print(f"  {CYAN}This may take several minutes on your system...{RESET}")
                            
                            result = subprocess.run(
                                pip_cmd,
                                capture_output=True,
                                text=True,
                                timeout=install_timeout
                            )
                        
                        if result.returncode == 0:
                            print(f"  {GREEN}✓ {display_name} {action}d successfully!{RESET}")
                            self.updated.append(display_name)
                        else:
                            print(f"  {RED}✗ Failed to {action} {display_name}{RESET}")
                            if result.stderr and not "externally-managed-environment" in result.stderr:
                                print(f"    Error: {result.stderr[:200]}")
                            self.failed.append(display_name)
                    
                    except subprocess.TimeoutExpired:
                        print(f"  {RED}✗ {action.capitalize()} timeout for {display_name}{RESET}")
                        self.failed.append(display_name)
                    
                    except Exception as e:
                        print(f"  {RED}✗ Error {action}ing {display_name}: {str(e)}{RESET}")
                        self.failed.append(display_name)
                else:
                    print(f"  {YELLOW}Skipped {display_name}{RESET}")
                    self.skipped.append(display_name)
    
    def print_summary(self):
        """Print a summary of actions taken"""
        print(f"\n{BRIGHT}=============================================={RESET}")
        print(f"{BRIGHT}                   SUMMARY{RESET}")
        print(f"{BRIGHT}=============================================={RESET}")
        
        if self.already_updated:
            print(f"{GREEN}✓ Up to date:{RESET} {', '.join(self.already_updated)}")
        
        if self.updated:
            print(f"{GREEN}✓ Updated:{RESET} {', '.join(self.updated)}")
        
        if self.skipped:
            print(f"{YELLOW}− Skipped:{RESET} {', '.join(self.skipped)}")
        
        if self.failed:
            print(f"{RED}✗ Failed:{RESET} {', '.join(self.failed)}")
        
        if not any([self.updated, self.skipped, self.failed, self.already_updated]):
            print(f"{CYAN}No actions taken.{RESET}")
        
        # Suggest --break-system-packages if needed and not used
        if self.needs_break_system and not self.break_system and self.failed:
            print(f"\n{YELLOW}ℹ Tip: Run with --break-system-packages flag to force updates{RESET}")
            print(f"  {CYAN}Example: python3 frup.py --break-system-packages --auto{RESET}")
        
        # Final status
        print(f"\n{BRIGHT}=============================================={RESET}")
        if self.check_only:
            print(f"{BRIGHT}     Check Complete! F.R.U. v1.0 END{RESET}")
        else:
            print(f"{BRIGHT}     Update Process Complete! F.R.U. v1.0 END{RESET}")
        print(f"{BRIGHT}=============================================={RESET}")
    
    def run(self):
        """Main execution flow"""
        self.print_header()
        
        # Fetch all versions
        self.fetch_online_versions()
        self.check_local_versions()
        
        # Compare and potentially update
        self.compare_and_update()
        
        # Show summary
        self.print_summary()


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description='Fast Reticulum Updater v1.0 - Update Reticulum ecosystem packages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  frup.py                  # Interactive mode
  frup.py --auto           # Auto-update all packages
  frup.py --check-only     # Only check versions without updating
  frup.py --quiet --auto   # Silent auto-update
  frup.py --save-config    # Save example config file
  frup.py -b --auto        # Auto-update with --break-system-packages

Changes in v1.0:
  - Added system detection (OS, architecture, desktop environment)
  - Automatically skips desktop-only packages (like Sideband) on headless systems
  - Detects Termux, Raspbian, Pi Zero, and other special environments
  - Shows system information before update checks
  - Extended timeout for slow systems (Pi Zero gets 5 minutes)
        """
    )
    
    parser.add_argument(
        '--auto', '-a',
        action='store_true',
        help='Automatically update all packages without prompting'
    )
    
    parser.add_argument(
        '--check-only', '-c',
        action='store_true',
        help='Only check versions without updating'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Minimal output (errors and summary only)'
    )
    
    parser.add_argument(
        '--save-config',
        action='store_true',
        help='Save an example configuration file and exit'
    )
    
    parser.add_argument(
        '--break-system-packages', '-b',
        action='store_true',
        help='Use --break-system-packages flag for pip (required on some systems)'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='Fast Reticulum Updater v1.0'
    )
    
    args = parser.parse_args()
    
    # Create updater instance
    updater = ReticulumUpdater(
        auto_update=args.auto,
        quiet=args.quiet,
        check_only=args.check_only,
        break_system=args.break_system_packages
    )
    
    # Handle config save
    if args.save_config:
        updater.save_example_config()
        sys.exit(0)
    
    try:
        # Run the updater
        updater.run()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{RESET}")
        sys.exit(1)
    
    # Wait for user input before exiting (unless in quiet mode)
    if not args.quiet:
        print()
        print("------------- Press ENTER to exit... ---------------")
        input()


if __name__ == "__main__":
    main()
