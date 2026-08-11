#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# functional_demo - one-shot bench installer (Frappe v15 / ERPNext v15)
#
# Usage (run from anywhere on the bench server):
#     bash apps/functional_demo/install.sh [site-name]
#     # site-name is optional - if omitted, the first site in sites/sites.txt
#     # is detected automatically.
#
# Fixes: "No module named 'functional_demo'" when running `bench install-app`
#
# Why this error happens: a manually-cloned/copied app is never registered in
# the bench's Python virtualenv, so `bench install-app` cannot import it and
# fails with ModuleNotFoundError - no matter how many times you retry.
# This script does the registration for you:
#   1. makes sure the app is listed in the bench's apps.txt
#   2. registers the app in the virtualenv (pip editable install)
#        - falls back to an offline-safe .pth sys.path entry if pip is blocked
#   3. verifies `import functional_demo` (the exact thing that was failing)
#   4. installs the app on the site and builds the assets
# -----------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"   # .../apps/functional_demo -> bench root
APP_DIR="$BENCH_ROOT/apps/functional_demo"
APP_NAME="functional_demo"

# --- site (optional - auto-detect) -------------------------------------------
SITE="${1:-}"
if [ -z "$SITE" ]; then
	SITE="$(grep -v '^#' "$BENCH_ROOT/sites/sites.txt" 2>/dev/null | head -1 || true)"
fi
if [ -z "$SITE" ]; then
	echo "Usage: bash apps/functional_demo/install.sh <site-name>"
	echo "       (or run it with no arguments on a bench that has a site)"
	exit 1
fi

echo "==> Bench root : $BENCH_ROOT"
echo "==> Site       : $SITE"

if [ ! -f "$APP_DIR/hooks.py" ]; then
	echo "ERROR: App folder not found at $APP_DIR"
	echo "       Expected layout: <bench>/apps/functional_demo/hooks.py"
	exit 1
fi

# --- find the virtualenv python ----------------------------------------------
PYENV="$BENCH_ROOT/env"
PYTHON_BIN=""
for c in "$PYENV/bin/python" "$PYENV"/bin/python3*; do
	[ -x "$c" ] && PYTHON_BIN="$c" && break
done
if [ -z "$PYTHON_BIN" ]; then
	echo "ERROR: could not find the bench virtualenv python under $PYENV/bin"
	exit 1
fi
PYTHON_PIP="$(dirname "$PYTHON_BIN")/pip"
echo "==> Venv python: $PYTHON_BIN"

# --- 0. make sure the app is listed in the bench's apps.txt ------------------
APPS_TXT="$BENCH_ROOT/apps.txt"
if [ -f "$APPS_TXT" ] && ! grep -qx "$APP_NAME" "$APPS_TXT" 2>/dev/null; then
	printf '\n%s\n' "$APP_NAME" >> "$APPS_TXT"
	echo "==> Added '$APP_NAME' to $APPS_TXT"
fi

# --- 1. make `import functional_demo` work -----------------------------------
import_ok() {
	"$PYTHON_BIN" -c "import $APP_NAME" >/dev/null 2>&1
}

if import_ok; then
	echo "==> import $APP_NAME: already OK"
else
	echo "==> Registering $APP_NAME in the virtualenv (pip editable install)..."
	PIP_OK=0
	(cd "$BENCH_ROOT" && bench pip install -e "$APP_DIR" >/dev/null 2>&1) && PIP_OK=1 || true
	if [ "$PIP_OK" != "1" ] && [ -x "$PYTHON_PIP" ]; then
		(cd "$BENCH_ROOT" && "$PYTHON_PIP" install -e "$APP_DIR" >/dev/null 2>&1) && PIP_OK=1 || true
	fi
	if [ "$PIP_OK" != "1" ] && [ -x "$PYTHON_PIP" ]; then
		(cd "$BENCH_ROOT" && "$PYTHON_PIP" install --no-build-isolation -e "$APP_DIR" >/dev/null 2>&1) && PIP_OK=1 || true
	fi

	if [ "$PIP_OK" = "1" ]; then
		echo "==> pip editable install: OK"
	else
		echo "==> pip install blocked - applying offline-safe .pth sys.path entry"
		SP_DIR="$("$PYTHON_BIN" -c 'import site; print(site.getsitepackages()[0])' 2>/dev/null || true)"
		[ -z "$SP_DIR" ] && SP_DIR="$(ls -d "$PYENV"/lib/python*/site-packages 2>/dev/null | head -1 || true)"
		if [ -z "$SP_DIR" ]; then
			echo "ERROR: could not locate site-packages for the venv at $PYENV"
			exit 1
		fi
		mkdir -p "$SP_DIR"
		echo "$APP_DIR" > "$SP_DIR/${APP_NAME}.pth"
		echo "==> Wrote $SP_DIR/${APP_NAME}.pth"
	fi

	if import_ok; then
		echo "==> import $APP_NAME: OK"
	else
		echo "ERROR: still cannot import $APP_NAME."
		echo "       If this is a permissions problem, run with sudo:"
		echo "         sudo bash apps/functional_demo/install.sh $SITE"
		exit 1
	fi
fi

# --- 2. install on the site --------------------------------------------------
echo "==> Installing $APP_NAME on site $SITE ..."
(cd "$BENCH_ROOT" && bench --site "$SITE" install-app "$APP_NAME")

# --- 3. build assets ---------------------------------------------------------
echo "==> Building assets ..."
(cd "$BENCH_ROOT" && bench build)

# --- 4. verify ---------------------------------------------------------------
echo "==> Verifying ..."
if (cd "$BENCH_ROOT" && bench --site "$SITE" list-apps 2>/dev/null | grep -qx "$APP_NAME"); then
	echo "============================================================"
	echo " DONE - $APP_NAME is installed on site '$SITE'"
	echo "============================================================"
else
	echo "NOTE: install finished but $APP_NAME is not in list-apps yet."
	echo "      Try:  bench --site $SITE migrate  &&  bench --site $SITE list-apps"
fi
