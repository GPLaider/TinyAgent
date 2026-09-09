# Agent access modes candidate v26

Three session-scoped choices: basic, read-only (mutations/commands ask), and
YOLO (allow within the existing runtime authority). These never select Android
Root or Developer. Rules are PATCHed to the backend session and survive reload.
Every switch writes the same rule keys so backend merge semantics cannot leave
the prior profile's wildcard/external-directory rule active.

Permission queue is reconciled with the actual /permission endpoint every two
seconds while the composer is mounted. Requests appear above the input with an
explicit waiting state and the upstream once/always/reject controls. Known
bundled harness reads are replied once only after checking the tool call ID and
exact read path. Signing directories are not broadly allowed in basic mode.
Mode changes invalidate older automatic response passes.

Pacman v25 real WebView check: read -> yolo -> basic -> yolo -> read -> basic,
each saved in backend and preserved after reload. evidence/pacman-access-v25.json.
v26 adds the mode-switch race guard. GUI build/typecheck, APK build/lint and
packaged-byte validation passed. APK SHA256:
b8d33a498517a250ef4f654084f203aedad3092700dbe6009f02eaa2d3e1a008.
Existing development signer retained. Source changes exported in
patches/opencode-mobile-ux.patch for phone self-build reproduction.

Lyriq1 OAuth/live-task diagnosis: model gpt-6-astra via openai had already
responded and executed shell. Three read tools were stalled on external_directory
approval (two harness files and /etc/os-release), not long model reasoning.
Exact reads approved once and next model steps resumed. A subsequent bootstrap
read blocked again; upgrading this UI preserves user data and requires runtime
restart. No OAuth credentials copied or printed.
