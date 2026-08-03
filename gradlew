#!/usr/bin/env bash
set -euo pipefail

self_path="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
cleanup() {
  rm -f "$self_path"
}
trap cleanup EXIT

if command -v sdkmanager >/dev/null 2>&1; then
  yes | sdkmanager --licenses >/dev/null 2>&1 || true
  sdkmanager 'platforms;android-36' 'build-tools;36.0.0' >/dev/null
fi

gradle_version="8.13"
gradle_root="${RUNNER_TEMP:-/tmp}/tianji-gradle-${gradle_version}"
gradle_zip="${gradle_root}/gradle-${gradle_version}-bin.zip"
gradle_bin="${gradle_root}/gradle-${gradle_version}/bin/gradle"

if [[ ! -x "$gradle_bin" ]]; then
  mkdir -p "$gradle_root"
  curl --fail --location --retry 3 --output "$gradle_zip" \
    "https://services.gradle.org/distributions/gradle-${gradle_version}-bin.zip"
  unzip -q -o "$gradle_zip" -d "$gradle_root"
fi

"$gradle_bin" --no-daemon "$@"
