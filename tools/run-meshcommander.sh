#!/usr/bin/env bash
# MeshCommander + tunnels TLS legacy vers Intel AMT.
#
# Extrait le 2026-09-18 du conteneur `meshcommander` (cree 2026-07-25), dont la
# conf n'existait que dans son Cmd inline. AMT parle un TLS ancien que les
# clients modernes refusent : d'ou UnsafeLegacyRenegotiation + SECLEVEL=0 dans
# les tunnels socat, et le DNAT qui redirige les ports AMT clairs (16992/16994)
# vers ces tunnels locaux (16993/16995 en amont = pas de boucle).
#
# UI : http://localhost:3000
set -euo pipefail

AMT="${AMT:-10.0.10.239}"
NAME="${NAME:-meshcommander}"
HOST_PORT="${HOST_PORT:-3000}"

docker rm -f "$NAME" 2>/dev/null || true

docker run -d \
  --name "$NAME" \
  --restart unless-stopped \
  --cap-add CAP_NET_ADMIN \
  --sysctl net.ipv4.conf.all.route_localnet=1 \
  -p "${HOST_PORT}:8080" \
  -e AMT="$AMT" \
  node:18-alpine \
  sh -c '
apk add --no-cache socat iptables >/tmp/a.log 2>&1
npm install -g meshcommander >/tmp/i.log 2>&1
cat > /etc/openssl-legacy.cnf <<EOF
openssl_conf = openssl_init
[openssl_init]
ssl_conf = ssl_sect
[ssl_sect]
system_default = sysdef
[sysdef]
Options = UnsafeLegacyRenegotiation
CipherString = DEFAULT:@SECLEVEL=0
EOF
export OPENSSL_CONF=/etc/openssl-legacy.cnf
(socat TCP-LISTEN:16992,fork,reuseaddr,bind=127.0.0.1 OPENSSL-CONNECT:$AMT:16993,verify=0,snihost=$AMT &)
(socat TCP-LISTEN:16994,fork,reuseaddr,bind=127.0.0.1 OPENSSL-CONNECT:$AMT:16995,verify=0,snihost=$AMT &)
iptables -t nat -A OUTPUT -p tcp -d $AMT --dport 16992 -j DNAT --to-destination 127.0.0.1:16992
iptables -t nat -A OUTPUT -p tcp -d $AMT --dport 16994 -j DNAT --to-destination 127.0.0.1:16994
(meshcommander &)
sleep 6
exec socat TCP-LISTEN:8080,fork,reuseaddr TCP:127.0.0.1:3000
'

echo "meshcommander -> http://localhost:${HOST_PORT}  (AMT ${AMT})"
