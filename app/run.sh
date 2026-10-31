#!/usr/bin/env bash
# Start Watch Me.
#
#   ./run.sh           http://127.0.0.1:8000   for this computer's browser
#   ./run.sh --https   https://<this Mac's Wi-Fi IP>:8443   for a phone on the same Wi-Fi
#
# A phone only lets a page use the microphone over https, so --https makes a
# certificate with mkcert. The phone has to trust mkcert's root certificate
# once; see README.md, "On your phone".
set -euo pipefail
cd "$(dirname "$0")"

if [[ "${1:-}" == "--https" ]]; then
  ip="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1)"
  mkdir -p certs
  if [[ ! -f "certs/$ip.pem" ]]; then
    mkcert -cert-file "certs/$ip.pem" -key-file "certs/$ip-key.pem" "$ip" localhost 127.0.0.1
  fi
  echo "Open https://$ip:8443 on your phone (same Wi-Fi)."
  exec uv run uvicorn watchme.main:app --host 0.0.0.0 --port 8443 \
    --ssl-certfile "certs/$ip.pem" --ssl-keyfile "certs/$ip-key.pem"
fi

echo "Open http://127.0.0.1:8000"
exec uv run uvicorn watchme.main:app --host 127.0.0.1 --port 8000
