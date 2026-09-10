#!/usr/bin/bash
set -eu
test "${TINYAGENT_EXECUTION_PROVIDER:-}" = fedora-local
export RUSTUP_HOME=/opt/tinyagent-build/rustup
export CARGO_HOME=/opt/tinyagent-build/cargo
export RUSTUP_TOOLCHAIN=1.85.0
export CARGO_BUILD_JOBS=2
export PUB_CACHE=/opt/tinyagent-build/pub-cache
export PATH="$CARGO_HOME/bin:/opt/tinyagent-build/flutter-3.27.4/bin:$PUB_CACHE/bin:$PATH"
export FLUTTER_SUPPRESS_ANALYTICS=true
export CI=true
export PERL=/usr/bin/perl
export RUST_COMPILE_TARGET=aarch64-linux-android
cd /workspace/tinyagent-six-builds/appflowy/frontend
cargo install --locked cargo-make --version 0.37.18
cargo install --locked cargo-ndk --version 3.5.4
dart pub global activate protoc_plugin 21.1.2
cargo make --profile development-android appflowy-core-dev-android
# Same upstream generator as cargo-make, with its supported progress output enabled.
/usr/bin/bash ./scripts/code_generation/generate.sh --verbose
cd appflowy_flutter
flutter build apk --debug --target-platform android-arm64
