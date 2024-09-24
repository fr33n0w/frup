import requests
import subprocess

# Print the title
print("==============================================")
print("      Fast Reticulum Updater v0.3 by F")
print("==============================================")

# List of packages to check
packages = [
    {'name': 'RNS', 'url': 'https://github.com/markqvist/Reticulum'},
    {'name': 'LXMF', 'url': 'https://github.com/markqvist/lxmf'},
    {'name': 'NomadNet', 'url': 'https://github.com/markqvist/nomadnet'},
    {'name': 'MeshChat', 'url': 'https://github.com/liamcottle/reticulum-meshchat', 'manual_install': True, 'skip_local_check': True, 'skip_version_comparison': True, 'online_only': True},
    {'name': 'Sideband', 'url': 'https://github.com/markqvist/Sideband', 'manual_install': True, 'skip_local_check': True, 'skip_version_comparison': True, 'online_only': True},
    {'name': 'RNode CE', 'url': 'https://github.com/liberatedsystems/RNode_Firmware_CE', 'manual_install': True, 'skip_local_check': True, 'skip_version_comparison': True, 'online_only': True}
]

# Online versions
print("\n**Latest GitHub Versions:**")
for package in packages:
    github_repo = package['url'].split('/')[-2] + '/' + package['url'].split('/')[-1]
    response = requests.get(f"https://api.github.com/repos/{github_repo}/releases/latest")
    if response.status_code == 200:
        latest_version = response.json()["tag_name"]
        print(f"* {package['name']}: {latest_version}")
    else:
        print(f"* {package['name']}: Failed to retrieve latest version from GitHub")

# Local versions
print("\n**Local Installed Versions:**")
for package in packages:
    if not ('skip_local_check' in package and package['skip_local_check']) and not ('online_only' in package and package['online_only']):
        try:
            pip_version = subprocess.check_output(["pip", "show", package['name']]).decode("utf-8")
            pip_version = [line.split(":")[1].strip() for line in pip_version.splitlines() if "Version:" in line][0]
            print(f"* {package['name']}: {pip_version}")
        except subprocess.CalledProcessError:
            print(f"* {package['name']}: Not installed via pip")

# Compare versions and ask to install/update
print("\n**Version Comparison for Update Installation:**")
for package in packages:
    if not ('skip_local_check' in package and package['skip_local_check']) and not ('skip_version_comparison' in package and package['skip_version_comparison']) and not ('online_only' in package and package['online_only']):
        github_repo = package['url'].split('/')[-2] + '/' + package['url'].split('/')[-1]
        response = requests.get(f"https://api.github.com/repos/{github_repo}/releases/latest")
        if response.status_code == 200:
            latest_version = response.json()["tag_name"]
        else:
            latest_version = None

        try:
            pip_version = subprocess.check_output(["pip", "show", package['name']]).decode("utf-8")
            pip_version = [line.split(":")[1].strip() for line in pip_version.splitlines() if "Version:" in line][0]
        except subprocess.CalledProcessError:
            pip_version = None

        print(f"* {package['name']}:")
        if pip_version == latest_version:
            print(f"  Up to date!")
        else:
            if 'manual_install' in package and package['manual_install']:
                print(f"  New version ({latest_version}) available. Please install it manually.")
            else:
                print(f"  New version ({latest_version}) available.")
                if pip_version is None:
                    print(f"  {package['name']} is not installed. Do you want to install it? (y/n)")
                else:
                    print(f"  Do you want to update {package['name']} to the latest version? (y/n)")
                response = input()
                if response.lower() == 'y':
                    print(f"  Installing/Updating {package['name']}...")
                    subprocess.run(["pip", "install", "--upgrade", package['name']])
                    print(f"  {package['name']} installed/updated successfully!")
                else:
                    print(f"  Skipping update of {package['name']}")

# Final message
print("\n=====================================================")
print("       Update process complete! F.R.U. v0.3 END")
print("=======================================================")