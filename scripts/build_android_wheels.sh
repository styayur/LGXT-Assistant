#!/usr/bin/env bash
# Candidate-only, reproducible source build; no upload to a package index.
set -eo pipefail
repo_root="$PWD"
forge_root="${RUNNER_TEMP:?}/lgxt-mobile-forge"
git clone https://github.com/flet-dev/mobile-forge.git "$forge_root"
git -C "$forge_root" checkout --detach b38989fa3954c8a491347bdce4196dedeacae399
cd "$forge_root"
export PYTHON_BUILD_RELEASE=20260921
export ANDROID_ABIS="arm64-v8a x86_64"
export NDK_HOME="$ANDROID_HOME/ndk/27.3.13750724"
"$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" 'ndk;27.3.13750724'
mkdir -p downloads
curl --fail --location --retry 3 -o downloads/python-android-mobile-forge-3.14.7.tar.gz \
  https://github.com/flet-dev/python-build/releases/download/20260921/python-android-mobile-forge-3.14.7.tar.gz
echo '57ff6e122d7c05523c1704f4ea2118445c38a80e13a533ab3d0e143e3d6545fc  downloads/python-android-mobile-forge-3.14.7.tar.gz' | sha256sum --check
curl --fail --location --retry 3 -o downloads/Pillow-13.0.0.tar.gz \
  https://files.pythonhosted.org/packages/ce/a4/9cc30690a394a8305e8be4c9036aa16d0dfddadd09079860b582f562496d/pillow-13.0.0.tar.gz
echo 'cdcd1ba258178f7356d74170c9a81ba4eab6a5d55748bc402a5a2a6fe6be3510  downloads/Pillow-13.0.0.tar.gz' | sha256sum --check
# Pin the cross compiler helper rather than following its branch at build time.
sed -i 's/crossenv@flet/crossenv@e5e615651f794d060d9484eab463861fef2a2019/' pyproject.toml
cp "$repo_root/packaging/android/pillow-13-android.patch" recipes/pillow/patches/setup-12.x.patch
source ./setup.sh 3.14.7 android
forge android pillow:13.0.0
mkdir -p "$repo_root/build/android/wheels" "$repo_root/build/android/wheel-evidence"
cp dist/pillow-13.0.0-*.whl "$repo_root/build/android/wheels/"
cp logs/*[Pp]illow* "$repo_root/build/android/wheel-evidence/"
python -m pip freeze > "$repo_root/build/android/wheel-evidence/build-environment.txt"
git diff > "$repo_root/build/android/wheel-evidence/forge.patch"
cp recipes/pillow/meta.yaml "$repo_root/build/android/wheel-evidence/recipe.yaml"
cd "$repo_root/build/android/wheels"
sha256sum *.whl > SHA256SUMS.txt
