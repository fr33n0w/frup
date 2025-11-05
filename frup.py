#!/usr/bin/env python3
"""
Fast Reticulum Updater v0.7
Author: F
Improvements: Efficiency, error handling, CLI arguments, colored output, summary
"""

import requests
import subprocess
import sys
import argparse
import json
import os
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

class ReticulumUpdater:
    def __init__(self, auto_update=False, quiet=False, check_only=False):
        self.auto_update = auto_update
        self.quiet = quiet
        self.check_only = check_only
        self.github_versions = {}
        self.local_versions = {}
        self.updated = []
        self.skipped = []
        self.failed = []
        self.already_updated = []
        self.using_custom_config = False
        self.config_path = None
        
        # Default packages - can be overridden by config file
        self.packages = [
            {'name': 'RNS', 'url': 'https://github.com/markqvist/Reticulum'},
            {'name': 'LXMF', 'url': 'https://github.com/markqvist/lxmf'},
            {'name': 'NomadNet', 'url': 'https://github.com/markqvist/nomadnet'},
            {'name': 'MeshChat', 'url': 'https://github.com/liamcottle/reticulum-meshchat', 
             'manual_install': True, 'skip_local_check': True, 'skip_version_comparison': True, 'online_only': True},
            {'name': 'Sideband', 'url': 'https://github.com/markqvist/Sideband', 
             'manual_install': True, 'skip_local_check': True, 'skip_version_comparison': True, 'online_only': True},
            {'name': 'RNode Stock', 'url': 'https://github.com/markqvist/RNode_Firmware', 
             'manual_install': True, 'skip_local_check': True, 'skip_version_comparison': True, 'online_only': True},
            {'name': 'RNode CE', 'url': 'https://github.com/liberatedsystems/RNode_Firmware_CE', 
             'manual_install': True, 'skip_local_check': True, 'skip_version_comparison': True, 'online_only': True},
            {'name': 'RNode Micro TN', 'url': 'https://github.com/attermann/microReticulum_Firmware', 
             'manual_install': True, 'skip_local_check': True, 'skip_version_comparison': True, 'online_only': True}
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
            "packages": self.packages,
            "comment": "Customize this file to add/remove packages to check"
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
            print(f"{BRIGHT}      Fast Reticulum Updater v0.7 by F{RESET}")
            print(f"{BRIGHT}=============================================={RESET}")
            
            # Show config status
            if self.using_custom_config:
                print(f"{CYAN}Using custom config: {self.config_path}{RESET}")
            else:
                print(f"{CYAN}Using default configuration{RESET}")
    
    def fetch_github_versions(self):
        """Fetch all GitHub versions in one pass"""
        if not self.quiet:
            print(f"\n{BRIGHT}** Fetching Latest GitHub Versions **{RESET}")
        
        for package in self.packages:
            repo_parts = package['url'].split('/')
            repo = f"{repo_parts[-2]}/{repo_parts[-1]}"
            
            try:
                response = requests.get(
                    f"https://api.github.com/repos/{repo}/releases/latest",
                    timeout=10,
                    headers={'Accept': 'application/vnd.github.v3+json'}
                )
                response.raise_for_status()
                version = response.json().get("tag_name", "Unknown")
                self.github_versions[package['name']] = version
                
                if not self.quiet:
                    print(f"  {GREEN}✓{RESET} {package['name']}: {CYAN}{version}{RESET}")
            
            except requests.exceptions.Timeout:
                self.github_versions[package['name']] = None
                if not self.quiet:
                    print(f"  {YELLOW}⚠{RESET} {package['name']}: Timeout")
            
            except requests.exceptions.RequestException as e:
                self.github_versions[package['name']] = None
                if not self.quiet:
                    print(f"  {RED}✗{RESET} {package['name']}: Failed to fetch")
    
    def check_local_versions(self):
        """Check locally installed versions"""
        if not self.quiet:
            print(f"\n{BRIGHT}** Local Installed Versions **{RESET}")
        
        for package in self.packages:
            # Skip packages marked as online_only or skip_local_check
            if package.get('skip_local_check') or package.get('online_only'):
                self.local_versions[package['name']] = None
                if not self.quiet and not package.get('online_only'):
                    print(f"  {YELLOW}−{RESET} {package['name']}: Skipped")
                continue
            
            try:
                result = subprocess.run(
                    ["pip", "show", package['name']], 
                    capture_output=True, 
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        if "Version:" in line:
                            version = line.split(":")[1].strip()
                            self.local_versions[package['name']] = version
                            if not self.quiet:
                                print(f"  {GREEN}✓{RESET} {package['name']}: {CYAN}{version}{RESET}")
                            break
                else:
                    self.local_versions[package['name']] = None
                    if not self.quiet:
                        print(f"  {YELLOW}−{RESET} {package['name']}: Not installed")
            
            except subprocess.TimeoutExpired:
                self.local_versions[package['name']] = None
                if not self.quiet:
                    print(f"  {YELLOW}⚠{RESET} {package['name']}: Check timeout")
            
            except Exception as e:
                self.local_versions[package['name']] = None
                if not self.quiet:
                    print(f"  {RED}✗{RESET} {package['name']}: Error checking")
    
    def compare_and_update(self):
        """Compare versions and optionally update packages"""
        if self.check_only:
            print(f"\n{BRIGHT}** Version Comparison (Check Only Mode) **{RESET}")
        else:
            print(f"\n{BRIGHT}** Version Comparison & Update **{RESET}")
        
        for package in self.packages:
            # Skip certain packages
            if package.get('skip_version_comparison') or package.get('online_only'):
                continue
            
            name = package['name']
            github_version = self.github_versions.get(name)
            local_version = self.local_versions.get(name)
            
            # Normalize versions for comparison
            norm_github = self.normalize_version(github_version)
            norm_local = self.normalize_version(local_version)
            
            print(f"\n{BRIGHT}{name}:{RESET}")
            
            # Check if versions could be retrieved
            if github_version is None:
                print(f"  {RED}Cannot compare - GitHub version unavailable{RESET}")
                self.failed.append(name)
                continue
            
            # Compare versions
            if local_version is None:
                print(f"  {YELLOW}Not installed{RESET} (Available: {CYAN}{github_version}{RESET})")
                action = "install"
                should_update = True
            elif norm_local == norm_github:
                print(f"  {GREEN}✓ Up to date!{RESET} ({CYAN}{local_version}{RESET})")
                self.already_updated.append(name)
                continue
            else:
                print(f"  {YELLOW}Update available:{RESET} {local_version} → {CYAN}{github_version}{RESET}")
                action = "update"
                should_update = True
            
            # Handle manual install packages
            if package.get('manual_install'):
                print(f"  {CYAN}ℹ Please {action} manually from: {package['url']}{RESET}")
                self.skipped.append(name)
                continue
            
            # Skip if check-only mode
            if self.check_only:
                continue
            
            # Handle updates
            if should_update:
                if self.auto_update:
                    response = 'y'
                    print(f"  {CYAN}Auto-{action}ing...{RESET}")
                else:
                    response = input(f"  Do you want to {action} {name}? (y/n): ").strip().lower()
                
                if response == 'y':
                    print(f"  {CYAN}{action.capitalize()}ing {name}...{RESET}")
                    try:
                        result = subprocess.run(
                            ["pip", "install", "--upgrade", name],
                            capture_output=True,
                            text=True,
                            timeout=120
                        )
                        
                        if result.returncode == 0:
                            print(f"  {GREEN}✓ {name} {action}d successfully!{RESET}")
                            self.updated.append(name)
                        else:
                            print(f"  {RED}✗ Failed to {action} {name}{RESET}")
                            if result.stderr:
                                print(f"    Error: {result.stderr[:200]}")
                            self.failed.append(name)
                    
                    except subprocess.TimeoutExpired:
                        print(f"  {RED}✗ {action.capitalize()} timeout for {name}{RESET}")
                        self.failed.append(name)
                    
                    except Exception as e:
                        print(f"  {RED}✗ Error {action}ing {name}: {str(e)}{RESET}")
                        self.failed.append(name)
                else:
                    print(f"  {YELLOW}Skipped {name}{RESET}")
                    self.skipped.append(name)
    
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
        
        # Final status
        print(f"\n{BRIGHT}=============================================={RESET}")
        if self.check_only:
            print(f"{BRIGHT}     Check Complete! F.R.U. v0.7 END{RESET}")
        else:
            print(f"{BRIGHT}     Update Process Complete! F.R.U. v0.7 END{RESET}")
        print(f"{BRIGHT}=============================================={RESET}")
    
    def run(self):
        """Main execution flow"""
        self.print_header()
        
        # Fetch all versions
        self.fetch_github_versions()
        self.check_local_versions()
        
        # Compare and potentially update
        self.compare_and_update()
        
        # Show summary
        self.print_summary()


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description='Fast Reticulum Updater v0.7 - Update Reticulum ecosystem packages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  frup.py                  # Interactive mode
  frup.py --auto           # Auto-update all packages
  frup.py --check-only     # Only check versions without updating
  frup.py --quiet --auto   # Silent auto-update
  frup.py --save-config    # Save example config file
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
        '--version', '-v',
        action='version',
        version='Fast Reticulum Updater v0.7'
    )
    
    args = parser.parse_args()
    
    # Create updater instance
    updater = ReticulumUpdater(
        auto_update=args.auto,
        quiet=args.quiet,
        check_only=args.check_only
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
