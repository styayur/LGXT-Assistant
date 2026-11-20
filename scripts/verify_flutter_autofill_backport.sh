#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
set -euo pipefail
repo_root=$(pwd)
python scripts/apply_flutter_autofill_backport.py --flutter-root "$FLUTTER_ROOT" \
  --output build/android/flutter-autofill-backport.json
cp packaging/flutter/tests/autofill_privacy_test.dart \
  "$FLUTTER_ROOT/packages/flutter/test/services/lgxt_autofill_privacy_test.dart"
(
  cd "$FLUTTER_ROOT/packages/flutter"
  flutter test --reporter expanded test/services/autofill_test.dart \
    test/services/lgxt_autofill_privacy_test.dart
) | tee "$repo_root/build/android/flutter-autofill-tests.log"
