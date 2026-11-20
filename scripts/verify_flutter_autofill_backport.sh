#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
set -euo pipefail
repo_root=$(pwd)
# This wrapper configures only the disposable CI build. The Python installer
# remains available for an explicitly selected SDK outside CI.
test "${GITHUB_ACTIONS:-}" = true
gradle_build_home="$RUNNER_TEMP/lgxt-gradle"
mkdir -p "$gradle_build_home/init.d"
cp packaging/android/kotlin-official-repository.init.gradle \
  "$gradle_build_home/init.d/lgxt-kotlin-official.gradle"
printf 'GRADLE_USER_HOME=%s\n' "$gradle_build_home" >> "$GITHUB_ENV"
export GRADLE_USER_HOME="$gradle_build_home"
python scripts/apply_flutter_autofill_backport.py --flutter-root "$FLUTTER_ROOT" \
  --output build/android/flutter-autofill-backport.json
cp packaging/flutter/tests/autofill_privacy_test.dart \
  "$FLUTTER_ROOT/packages/flutter/test/services/lgxt_autofill_privacy_test.dart"
(
  cd "$FLUTTER_ROOT/packages/flutter"
  flutter test --reporter expanded test/services/autofill_test.dart \
    test/services/lgxt_autofill_privacy_test.dart
) | tee "$repo_root/build/android/flutter-autofill-tests.log"
