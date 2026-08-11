#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# functional_demo - one-shot bench installer
#
# Run from the bench root (e.g. ~/frappe-bench-v15):
#     bash apps/functional_demo/install.sh <site-name>
#
# This fixes the "No module named 'functional_demo'" error. The error happens
# because a manually-cloned app is never registered in the bench's Python
# virtualenv. This script does that registration (and only then installs the
# app on your site):
#   1. pip editable install  -> needs internet, the "proper" way
#   2. .pth fallback         -> works offline, writes the app dir to sys.path
#   3. verify import         -> confirms `import functional_demo` works
#   4. install-app + build
# -----------------------------------------------------------------------------
set -euo pipefail

SITE="${1:-}"
if [ -z "$SITE" ]; then
	echo "Usage: bash apps/functional_demo/install.sh <site-name>"
	echo "Example: bash apps/functional_demo/install.sh fd.bizaxl.local"
	exit 1
fi

BENCH_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APP_DIR="$BENCH_ROOT/apps/functional_demo"
PYENV="$BENCH_ROOT/env"

if [ ! -f "$APP_DIR/hooks.py" ]; then
	echo "ERROR: App folder not found at $APP_DIR"
	echo "Clone it first:  bench get-app https://github.com/Sudhakar1110/functional_demo"
	exit 1
fi

# find the venv python (bin/python, bin/python3, bin/python3.11, ...)
PYTHON_BIN=""
if [ -x "$PYENV/bin/python" ]; then
	PYTHON_BIN="$PYENV/bin/python"
else
	PYTHON_BIN="$(ls "$PYENV"/bin/python* 2>/dev/null | head -1 || true)"
fi

echo "==> Bench root : $BENCH_ROOT"
echo "==> Site       : $SITE"
echo "==> Venv python: ${PYTHON_BIN:-<none>}"

# --- Step 1: make `import functional_demo` work -----------------------------
import_ok() {
	[ -n "$PYTHON_BIN" ] && "$PYTHON_BIN" -c "import functional_demo" >/dev/null 2>&1
}

if import_ok; then
	echo "==> functional_demo is already importable - OK"
else
	echo "==> Registering app in the virtualenv (pip editable install)..."
	if (cd "$BENCH_ROOT" && bench pip install -e apps/functional_demo >/dev/null 2>&1); then
		echo "==> pip editable install: OK"
	else
		echo "==> pip install unavailable - applying .pth sys.path fallback (offline-safe)"
		SP_DIR="$(ls -d "$PYENV"/lib/python*/site-packages 2>/dev/null | head -1 || true)"
		if [ -z "$SP_DIR" ]; then
			echo "ERROR: could not locate site-packages under $PYENV"
			exit 1
		fi
		# the app package lives at <bench>/apps/functional_demo/functional_demo/
		# so the project root (apps/functional_demo) must be on sys.path
		echo "$APP_DIR" > "$SP_DIR/frappe_apps.pth"
		echo "==> Wrote $SP_DIR/frappe_apps.pth"
	fi

	if import_ok; then
		echo "==> import functional_demo: OK"
	else
		echo "ERROR: still cannot import functional_demo."
		echo "       Check the venv: $PYENV"
		exit 1
	fi
fi

# --- Step 2: install on the site --------------------------------------------
echo "==> Installing functional_demo on site $SITE ..."
(cd "$BENCH_ROOT" && bench --site "$SITE" install-app functional_demo)

# --- Step 3: build assets ----------------------------------------------------
echo "==> Building assets ..."
(cd "$BENCH_ROOT" && bench build)

echo ""
echo "============================================================"
echo " DONE - functional_demo is installed on site '$SITE'"
echo "============================================================"
