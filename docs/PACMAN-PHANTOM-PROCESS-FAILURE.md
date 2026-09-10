# Pacman build runtime termination — 2026-09-10

During Lyriq1 UI validation, the existing Pacman VLC build status probe lost its HTTP connection. Read-only process inspection found the TinyAgent application still alive (PID4408, UID10223), with no PRoot/OpenCode/compiler/build-waiter processes remaining. Runtime preferences recorded `환경 준비 실패: 백엔드 종료 exit=137 · linux/backend.log 확인`; backend.log contained only the original listening message.

Android events log proves the cause category. At device time 15:04:30.800, ActivityManager killed PID4785 libproot.so with reason `Trimming phantom processes`; at .801 it killed PID4789 opencode with the same reason. bash, python3, and flock children were killed immediately afterward. Evidence: `evidence/pacman-phantom-process-kill.txt`.

This is confirmed Android phantom-process trimming, not an inferred OOM, dnfast defect, successful workload completion, or observation timeout. At inspection MemAvailable was 8046308 KiB; this post-exit figure does not establish memory availability before the kill. `device_config get activity_manager max_phantom_processes` and `settings get global settings_enable_monitor_phantom_procs` both returned null; null is not a verified numeric/default limit.

VLC was last observed in native configure/build work. AppFlowy retry and TinyAgent self-build had live shell requests waiting on the shared flock build slot. Their processes are now gone, so these are interrupted workloads, not still-running waiters. No successful APK/result is asserted. No restart, package deletion, reset, or global monitor/limit change was performed during diagnosis.

Next: collect the preserved workload checkpoints/logs; eliminate live shell/process trees for queued jobs; measure process counts and bound toolchain parallelism; restart only the selected interrupted workload after instrumentation. Stock acceptance must not rely on an ADB-only global phantom-process bypass. Verify recovery and honest interrupted-session state as part of the release gate.

## First recovery and reduced-process retry

Recovered the existing runtime through its native “환경 준비 다시 시도” control; no reinstall, clear-data, or global Android setting changes. New app-owned PRoot PID22856 and OpenCode PID22860 appeared under UID10223 while app PID4408 remained. Preserved VLC run `vlc-android-build-1789017118644979658` still has its logs; its last commands show GMP compiling concurrently with `meson compile -C librist/build` / Ninja. Its old result.json still says running; this is stale after the confirmed kernel kill.

`build-workload.py` now acquires the existing flock non-blockingly before preflight. Busy slots and missing prepared toolchains exit 75 with BUILD_NOT_STARTED, rather than holding a waiting Python/shell tree. This is admission refusal, not a durable queue implementation. Do not launch AppFlowy or self-build waiting shells alongside the active VLC retry.

Default per-tool jobs is now 1, explicitly selectable as 1 or 2. Gradle, Go, Cargo, CMake and Organic Maps receive the selected limit. VLC receives `MAKEFLAGS=-j1 MESONCOMPILEFLAGS=-j1`; its pinned contrib/src/main.mak exposes MESONCOMPILEFLAGS to meson compile, whereas Make's -j2 alone did not cap that invocation. AppFlowy's Rust wrapper honors TINYAGENT_BUILD_JOBS. This bounds supported build-tool settings, not all possible application child processes.

Phone regression `check-build-admission.py` holds the real lock and launches the actual build script. Before: child remained blocked for five seconds and the check failed (session `ses_f76046fccffeffF4m15N0lX101`). After: child exited 75, no new build result directory was created, and nested GNU Make retained Meson -j1 (session `ses_f7603ab63ffeSbUzuO57rBxPBW`). Evidence: `pacman-admission-before.json`, `pacman-admission-after.json`. The test kills only its own known child on timeout.

Only VLC was relaunched: session `ses_f7602a040ffexZctrjigdpFcaW`, run `vlc-android-build-1789021480245204534`, command `/usr/bin/python3 /shared/build-workload.py vlc-android --jobs 1`. It acquired the slot and began executing. Initial observed UID process count was 11, including app/PRoot/OpenCode and Java initialization (`pacman-process-limited-sample.json`). This is one sample, not a proven peak or stability pass. Continue observing through the previous Meson/Ninja failure point and APK production.

Additional recovery defect: after runtime recovery, the original killed VLC session still returns a persisted tool state of running. Its abort endpoint returned true, yet readback still showed that stale running part (`pacman-vlc-orphan-after-abort.json`). Do not treat that old part as a live job. Startup reconciliation of interrupted tool records remains required; no direct database edits or false completion markings were performed.
