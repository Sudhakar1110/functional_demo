#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# functional_demo - one-shot bench installer
#
# Run from the bench root (e.g. ~/frappe-bench-v15):
#     bash apps/functional_demo/install.sh <site-name>
#
# What it does:
#   1. Registers the app in the bench virtualenv (editable pip install) so
#      `import functional_demo` works - this is the step that fixes the
#      "No module named 'functional_demo'" error.
#   2. Falls back to a .pth sys.path entry if pip is unavailable.
#   3. Installs the app on the site and builds assets.
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

echo "==> Bench root : $BENCH_ROOT"
echo "==> Site       : $SITE"

# --- 1. register the app in the virtualenv ---------------------------------
if [ -d "$PYENV" ]; then
	if (cd "$BENCH_ROOT" && bench pip install -e apps/functional_demo >/dev/null 2>&1); then
		echo "==> App registered via pip editable install"
	else
		echo "==> pip install failed - using .pth sys.path fallback"
		PYVER_DIR="$(ls -d "$PYENV"/lib/python*/site-packages 2>/dev/null | head -1 || true)"
		if [ -z "$PYVER_DIR" ]; then
			echo "ERROR: could not locate site-packages under $PYENV"
			exit 1
		fi
		echo "$BENCH_ROOT/apps" > "$PYVER_DIR/frappe_apps.pth"
		echo "==> Wrote $PYVER_DIR/frappe_apps.pth"
	fi
else
	echo "==> No virtualenv found at $PYENV - assuming apps are on PYTHONPATH already"
fi

# --- 2. verify import works -------------------------------------------------
if (cd "$BENCH_ROOT" && bench execute "frappe.utils.install.get_installed_apps" >/dev/null 2>&1 \
	&& python -c "import functional_demo" >/dev/null 2>&1); then
	echo "==> import functional_demo: OK"
else
	# python inside the venv
	if [ -x "$PYENV/bin/python" ] && "$PYENV/bin/python" -c "import functional_demo" >/dev/null 2>&1; then
		echo "==> import functional_demo: OK (venv python)"
	else
		echo "WARNING: could not verify import; continuing anyway"
	fi
fi

# --- 3. install on site -----------------------------------------------------
echo "==> Installing functional_demo on site $SITE ..."
(cd "$BENCH_ROOT" && bench --site "$SITE" install-app functional_demo)

echo "==> Building assets ..."
(cd "$BENCH_ROOT" && bench build)

echo ""
echo "✅ DONE - functional_demo is installed on site '$SITE'"
