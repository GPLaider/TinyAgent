# Preparation progress candidate v23

App preparation button swaps to a progress panel immediately; duplicate starts
are blocked while the service prepares. UI restoration reads current service
state and shared progress. Percentages are per stage, not a fabricated total.

Measured stages: compressed asset bytes copied; extracted entry counts (5638
Fedora entries and 1 OpenCode entry, bound to existing archive SHA256 pins).
Package-manager output is streamed with current item/total when available;
repository metadata and unmeasurable post-install work remain indeterminate.
Details include elapsed time. The same status and percent update notification1.
Failure leaves a notification with retry/open actions and app diagnostics.
No-network first preparation produces an actionable internet-required message.
Preparation holds a partial CPU wake lock, released on ready/error/cancel/destroy,
with a one-hour maximum hold. This is not a blanket bypass of Android Doze/network
restrictions. The running idle backend does not hold this preparation lock.

Build/lint and packaged validation passed. Pacman v21 button swap test passed;
v23 fresh extraction and notification percent observed while screen off.
Existing Pacman build rootfs was moved to rootfs-before-progress-test for this
test, not deleted. Workspace, source, outputs, and signing identity preserved.
The original rootfs must be restored after the test completes.

Fresh background preparation completed on v23 while the display remained off.
Notification showed measured 77% extraction and package-item progress. The first
test assertion incorrectly matched historical wake-lock events; live power state
showed Wake Locks: size=0 and the matching REL event at completion. Observer now
checks only active locks. Original Pacman rootfs restored; the completed test
rootfs is preserved as rootfs-progress-test-complete. v24 simplifies package
progress labels to Korean, retaining numerical progress; build/lint passed and
the original build environment resumed. Included in v26 access-mode candidate.

Lyriq1 retains the Pacman-built APK (a614e166...), not this host-built candidate.
Its first preparation completed and app-UID PRoot/OpenCode processes were verified.
