# ApexEngine Max Mobile v3.0

No root. All VIP features. Auto Setup.

## Build

Linux or WSL2 only. Buildozer doesn't run on Windows/macOS natively.

```bash
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf \
  libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev \
  cmake libffi-dev libssl-dev
pip install --user --upgrade buildozer cython virtualenv
cd ApexEngineMaxMobile
buildozer -v android debug