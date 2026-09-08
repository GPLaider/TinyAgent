# LibADB Android BC

Source: https://github.com/osservatorionessuno/libadb-android-bc
Commit: 0bab7639f7110a4c0a09a2ff2b6c61cf19ac70d5
Imported: libadb/src/main/java, COPYING, LICENSES (2026-09-08).
Use the Apache-2.0 option for dual-licensed files; preserve per-file notices and
all additional licenses. The source snapshot avoids a JitPack build dependency.
BouncyCastle 1.84 dependencies are resolved from Maven Central.
Local patch: PairingConnectionCtx retains its socket for cancellation and uses
15-second connect/read timeouts. Original protocol and cryptography unchanged.
