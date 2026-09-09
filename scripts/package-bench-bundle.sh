#!/usr/bin/bash
set -eu
cd /work/output
mkdir -p micro-root bundle/dnfast/bin bundle/dnfast/lib bundle/microdnf/bin bundle/microdnf/lib
for rpm in rpms/*.rpm; do
    (cd micro-root; rpm2cpio "/work/output/$rpm" | cpio --quiet -idmu)
done
python3 /work/bundle.py
tar -czf /work/output/package-bench-arm64.tar.gz -C /work/output/bundle .
sha256sum /work/output/package-bench-arm64.tar.gz
