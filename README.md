# 📱 AndrobianOS Installation Guide

The complete, step-by-step guide to installing AndrobianOS on your Android tablet using Termux. Please follow these instructions sequentially to ensure a successful setup.


<p align="center">
  <img width="854" height="214" alt="boot animation" src="https://github.com/user-attachments/assets/3ee63624-0e2d-4fae-b8e8-0f2876d3f75b" />
</p>

## 📑 Table of Contents
1. [Phase 1: Android Settings](#phase-1-android-settings)
2. [Phase 2: Termux Environment Setup](#phase-2-termux-environment-setup)
3. [Phase 3: Debian Subsystem Setup](#phase-3-debian-subsystem-setup)
4. [Phase 4: Startup Automation](#phase-4-startup-automation)
5. [Phase 5: Launch & Troubleshooting](#phase-5-launch--troubleshooting)

---

## ⚙️ Phase 1: Android Settings
*Perform these steps in your device's native settings before opening Termux.*

1. **Enable Developer Mode:** * Navigate to `Settings` > `About Phone`.
   * Tap `MIUI Version` (or `Build Number`) **7 times** until Developer Mode is enabled.
2. **Disable Child Process Restrictions:** * Navigate to `Settings` > `Additional Settings` > `Developer Options`.
   * Toggle **ON** `Disable child process restrictions`.
3. **Remove Battery Restrictions for Termux:** * Navigate to `Settings` > `Apps` > `Termux` > `Battery`.
   * Set to **No restrictions** (or "Unrestricted").

---

## 💻 Phase 2: Termux Environment Setup
*Open the Termux app. Type each command, press `Enter`, and wait for the process to finish completely before moving to the next.*

### 1. Grant Storage Access
```bash
termux-setup-storage

```
> **Note:** Tap **Allow** on the popup that appears on your screen.
> 
### 2. Update Termux Packages
*(This takes 3–5 minutes. It is normal to see many lines scrolling by.)*
```bash
pkg update -y && pkg upgrade -y

```
### 3. Install X11 Display Tools
```bash
pkg install -y x11-repo
pkg install -y termux-x11-nightly

```
### 4. Install GPU Drivers
*(To avoid dependency conflicts with deprecated Android loaders, we use the generic loader or omit it entirely. If these fail, the desktop will gracefully fall back to software rendering.)*
```bash
pkg install -y mesa 2>/dev/null || echo "mesa skipped"
pkg install -y mesa-vulkan-icd-freedreno vulkan-loader-generic 2>/dev/null || echo "GPU driver not available - will use software rendering"

```
> **Troubleshooting Dependency Conflicts:** If you encounter "held broken packages" from a previous attempt, run apt --fix-broken install followed by pkg update -y && pkg upgrade -y before retrying the GPU driver installation.
> 
### 5. Install Core Utilities
```bash
pkg install -y proot-distro git curl wget pulseaudio termux-api

```
### 6. Configure Display & Audio Environment Variables
```bash
echo 'export DISPLAY=:0' >> ~/.bashrc
echo 'export PULSE_SERVER=tcp:127.0.0.1:4713' >> ~/.bashrc
source ~/.bashrc

```
### 7. Install Debian Linux
*(Downloads ~150 MB. Takes 3–10 minutes.)*
```bash
proot-distro install debian

```
## 🐧 Phase 3: Debian Subsystem Setup
*Enter the Debian environment. Your prompt will change to root@localhost:~#.*
```bash
proot-distro login debian --user root

```
### 1. Update Debian
```bash
apt update -y && apt upgrade -y

```
### 2. Configure Locales
*(This prevents Perl warnings during installations.)*
```bash
apt install -y locales && locale-gen en_US.UTF-8

```
### 3. Install Required System Packages
```bash
apt install -y python3 python3-pip python3-tk python3-pil git curl wget ca-certificates ghostscript tmux

```
### 4. Install Python Libraries
```bash
pip3 install --break-system-packages pymupdf Pillow

```
> **Note:** If --break-system-packages returns an error, use: pip3 install pymupdf Pillow --user
> 
### 5. Clone the AndrobianOS Repository
*(Replace suvadippatra with your actual GitHub username if forking. The credential helper flag ensures it bypasses password prompts for public repositories.)*
```bash
git -c credential.helper='' clone --depth 1 [https://github.com/suvadippatra/androbian-os.git](https://github.com/suvadippatra/androbian-os.git) /opt/androbian

```
**Verify the clone:**
```bash
ls /opt/androbian/

```
*(You should see files like launcher.py, theme.py, splash.py, bootstrap.sh, etc.)*
### 6. Run Desktop Setup Scripts
```bash
bash /opt/androbian/create_desktop_entries.sh

```
### 7. Install Desktop Environment (LXQt & Openbox)
*(This is a large installation and takes 10–20 minutes. Configuration prompts will auto-complete.)*
```bash
apt install -y lxqt-core openbox pcmanfm-qt lxqt-panel qt5ct plank picom kvantum fonts-inter adwaita-icon-theme falkon

```
> **Fallback:** If a single package fails (like falkon or fonts-inter), omit it and run the command again with the remaining packages.
> 
### 8. Create User Account
```bash
useradd -m -s /bin/bash joydip
passwd joydip

```
*(Type your password twice. Keystrokes will remain invisible for security.)*
**Configure Permissions & Directories:**
```bash
echo "joydip ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
mkdir -p /home/joydip/Desktop /home/joydip/android_storage

```
### 9. Configure Desktop & Themes
```bash
mkdir -p /etc
cp /opt/androbian/picom.conf /etc/picom.conf

mkdir -p /home/joydip/.config/openbox
cat > /home/joydip/.config/openbox/autostart << 'EOF'
picom --config /etc/picom.conf &
sleep 0.4
lxqt-panel &
sleep 0.3
plank &
sleep 0.2
python3 /opt/androbian/touch_manager.py &
EOF

mkdir -p /home/joydip/.config/qt5ct
cat > /home/joydip/.config/qt5ct/qt5ct.conf << 'EOF'
[Appearance]
style=kvantum-dark
icon_theme=Adwaita

[Fonts]
general="Inter,11,-1,5,50,0,0,0,0,0"
EOF

echo 'export QT_QPA_PLATFORMTHEME=qt5ct' >> /home/joydip/.bashrc

```
### 10. Create the Desktop Launch Command (joy)
```bash
cat > /usr/local/bin/joy << 'JOYEOF'
#!/bin/bash
export DISPLAY=:0
export PULSE_SERVER=tcp:127.0.0.1:4713
export QT_QPA_PLATFORMTHEME=qt5ct
openbox --replace &>/dev/null &
sleep 0.5
picom --config /etc/picom.conf &>/dev/null &
sleep 0.3
plank &>/dev/null &
python3 /opt/androbian/splash.py
JOYEOF

chmod +x /usr/local/bin/joy

```
### 11. Verify Installations
```bash
python3 -c "import fitz; print('PyMuPDF OK')"
python3 -c "import tkinter; print('tkinter OK')"
ls /opt/androbian/launcher.py && echo "Suite files OK"

```
### 12. Exit Debian
```bash
exit

```
## 🚀 Phase 4: Startup Automation
*You should now be back at the Termux $ prompt.*
Create the startup script to initialize the GUI and audio servers:
```bash
cat > ~/start_desktop.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
am start --user 0 -n com.termux.x11/com.termux.x11.MainActivity &
sleep 3
pulseaudio --start --load="module-native-protocol-tcp auth-ip-acl=127.0.0.1" --exit-idle-time=-1 &
proot-distro login debian --bind /sdcard:/home/joydip/android_storage --user joydip -- bash -ic 'export DISPLAY=:0 PULSE_SERVER=tcp:127.0.0.1:4713; joy'
EOF

chmod +x ~/start_desktop.sh
echo 'alias joy="bash ~/start_desktop.sh"' >> ~/.bashrc
source ~/.bashrc

```
## 🎉 Phase 5: Launch & Troubleshooting
To start your desktop at any time, simply open Termux and type:
```bash
joy

```
*Termux:X11 will open automatically. A boot animation will play, and the desktop will appear within 20–30 seconds.*
### 🛠️ Troubleshooting Guide
| Error | Solution |
|---|---|
| **Git prompts for username/password** | Your repository is set to Private. Go to GitHub > Repository > Settings > Danger Zone > Change visibility > **Public**. |
| **lxqt-core installation fails** | Run apt install -y lxqt-core again; the package manager will resume where it left off. |
| **joy: command not found in Termux** | Ensure you completed Phase 4. Verify by running cat ~/start_desktop.sh. |
| **Black screen after running joy** | Manually open the Termux:X11 app once to let it initialize, close it, and run joy in Termux again. |
| **Any Package "404 Not Found" Error** | Run apt update -y first to refresh repository links, then retry installing the specific package. |
```

---
> **`// SYS_ACK_INIT:`** `Compilation and logic processing powered with thanks to Claude.` 🤖
