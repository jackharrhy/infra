#!/bin/bash
# Review-only synthetic tests. No Docker or host network/services are used.
set -euo pipefail
if [[ $# != 2 ]]; then
  echo 'Usage: bash sandbox-check.sh /absolute/vector /absolute/vmauth' >&2
  exit 2
fi
source_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
vector=$(realpath -e -- "$1")
vmauth=$(realpath -e -- "$2")
exec timeout 45 bwrap \
  --unshare-all --die-with-parent --new-session \
  --ro-bind /usr /usr --ro-bind /lib /lib --ro-bind /lib64 /lib64 \
  --ro-bind "$source_dir" /source --ro-bind "$vector" /vector --ro-bind "$vmauth" /vmauth \
  --proc /proc --dev /dev --size 67108864 --tmpfs /tmp --chdir /source \
  --clearenv --setenv PATH /usr/bin --setenv HOME /tmp --setenv TMPDIR /tmp \
  --setenv PYTHONDONTWRITEBYTECODE 1 --setenv GOMEMLIMIT 128MiB --setenv GOMAXPROCS 2 \
  --setenv VMAUTH_TEST_BINARY /vmauth \
  --setenv LOG_WRITE_HOST logs.example.invalid --setenv LOG_WRITE_PASSWORD synthetic-fixture-only \
  -- /usr/bin/prlimit --cpu=30 --as=2147483648 --nproc=64 --fsize=8388608 -- /usr/bin/bash -c '
    set -euo pipefail
    python3 -m unittest discover -s /source -p "test_*.py" -v
    python3 /source/generate.py /source/synthetic-inventory.json /tmp/rendered
    /vector --threads 1 validate --no-environment --dangerously-allow-env-var-interpolation /tmp/rendered/vector.yaml
    /vector --threads 1 test --dangerously-allow-env-var-interpolation /tmp/rendered/vector.yaml
    /vmauth -dryRun -auth.config=/source/vmauth.yaml.example
  '
