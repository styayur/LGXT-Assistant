#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
set -euo pipefail

test "${GITHUB_ACTIONS:-}" = true
serial=$(adb devices | awk '$1 ~ /^emulator-[0-9]+$/ && $2=="device" {print $1}')
[[ "$serial" =~ ^emulator-[0-9]+$ ]]
# Only this disposable remote emulator's radios/clipboard are used.
adb -s "$serial" shell svc wifi disable
adb -s "$serial" shell svc data disable
python scripts/check_android_input_fidelity.py --serial "$serial" \
  --apk build/android/input-artifacts/LGXT-input-fidelity-test-only.apk \
  --identity build/android/input-artifacts/identity.json \
  --ime-apk build/android/input-ime/LGXT-test-ime.apk
