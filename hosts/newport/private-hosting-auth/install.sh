#!/usr/bin/env bash
set -euo pipefail
umask 077
cd -- "$(dirname -- "$0")"
state=$HOME/.local/state/infra/private-hosting-auth
image=quay.io/oauth2-proxy/oauth2-proxy:v7.15.6@sha256:c3415e8660af553f5e18f5d90db050614c02493c0ac6260ac59442f6d9b12048
if [[ ${1:-} == --slides ]]; then
  GOCACHE="$state/go-build" CGO_ENABLED=0 GOTOOLCHAIN=local go build -trimpath -o "$state/slides-gateway.new" main.go
  mv "$state/slides-gateway.new" "$state/slides-gateway"
  install -Dm644 private-hosting-slides.service "$HOME/.config/systemd/user/private-hosting-slides.service"
  systemctl --user daemon-reload
  systemctl --user enable private-hosting-slides.service
  systemctl --user restart private-hosting-slides.service
  exit
fi
for app in atlas go-demo; do
  case $app in atlas) port=21981;; go-demo) port=21982;; esac
  host=$app.pi.jackharrhy.dev
  dir=$state/$app
  mkdir -p "$dir"
  jq -e --arg host "$host" '.hosts | index($host) != null' "$state/provider.json" >/dev/null
  jq -erj '.secret | select(type=="string" and length>0)' "$state/provider.json" > "$dir/client-secret"
  if [[ ! -s $dir/cookie-key ]]; then openssl rand 32 > "$dir/cookie-key"; fi
  {
    jq -er '"client_id = " + (.client | tostring | @json)' "$state/provider.json"
    cat <<EOF
provider = "oidc"
oidc_issuer_url = "https://auth.jackharrhy.dev"
client_secret_file = "/credentials/client-secret"
cookie_secret_file = "/credentials/cookie-key"
redirect_url = "https://$host/oauth2/callback"
http_address = "127.0.0.1:$port"
upstreams = ["static://202"]
scope = "openid email profile"
code_challenge_method = "S256"
insecure_oidc_skip_nonce = false
email_domains = ["*"]
set_xauthrequest = true
pass_access_token = false
pass_authorization_header = false
set_authorization_header = false
cookie_name = "__Host-private-hosting"
cookie_secure = true
cookie_httponly = true
cookie_samesite = "lax"
cookie_path = "/"
cookie_expire = "1h"
cookie_refresh = "0s"
reverse_proxy = false
request_logging = false
auth_logging = false
EOF
  } > "$dir/proxy.toml"
  name=private-hosting-auth-$app
  if ! docker container inspect "$name" >/dev/null 2>&1; then
    docker run -d --name "$name" --restart unless-stopped --network host \
      --read-only --cap-drop ALL --security-opt no-new-privileges --user "$(id -u):$(id -g)" \
      --mount "type=bind,source=$dir,target=/credentials,readonly" "$image" --config=/credentials/proxy.toml >/dev/null
  else
    docker restart "$name" >/dev/null
  fi
done
GOCACHE="$state/go-build" CGO_ENABLED=0 GOTOOLCHAIN=local go build -trimpath -o "$state/gateway.new" main.go
mv "$state/gateway.new" "$state/gateway"
install -Dm644 private-hosting-auth.service "$HOME/.config/systemd/user/private-hosting-auth.service"
systemctl --user daemon-reload
systemctl --user enable private-hosting-auth.service
systemctl --user restart private-hosting-auth.service
