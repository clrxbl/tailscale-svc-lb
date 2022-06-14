#!/bin/bash

# Original: https://github.com/tailscale/tailscale/blob/3b55bf93062cc513a38a3dace3f49f48d3654202/docs/k8s/run.sh
# Copyright (c) 2022 Tailscale Inc & AUTHORS All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

export PATH=$PATH:/tailscale/bin

TS_AUTH_KEY="${TS_AUTH_KEY:-}"
TS_DEST_IP="${TS_DEST_IP:-}"
TS_EXTRA_ARGS="${TS_EXTRA_ARGS:-}"
TS_ACCEPT_DNS="${TS_ACCEPT_DNS:-false}"
TS_KUBE_SECRET="${TS_KUBE_SECRET:-tailscale}"

set -e

TAILSCALED_ARGS="--state=kube:${TS_KUBE_SECRET} --socket=/tmp/tailscaled.sock"

if [ $(cat /proc/sys/net/ipv4/ip_forward) != 1 ]; then
  echo "IPv4 forwarding (/proc/sys/net/ipv4/ip_forward) needs to be enabled, exiting..."
  exit 1
fi

echo "Waiting for leader election..."
LEADER=false
while [[ "${LEADER}" == "false" ]]; do
  CURRENT_LEADER=$(curl http://127.0.0.1:4040 -s -m 2 | jq -r ".name")
  if [[ "${CURRENT_LEADER}" == "$(hostname)" ]]; then
    echo "I am the leader."
    LEADER=true
  fi
  sleep 1
done

echo "Starting tailscaled"
tailscaled ${TAILSCALED_ARGS} &
PID=$!

UP_ARGS="--accept-dns=${TS_ACCEPT_DNS}"
if [[ ! -z "${TS_AUTH_KEY}" ]]; then
  UP_ARGS="--authkey=${TS_AUTH_KEY} ${UP_ARGS}"
fi
if [[ ! -z "${TS_EXTRA_ARGS}" ]]; then
  UP_ARGS="${UP_ARGS} ${TS_EXTRA_ARGS:-}"
fi

echo "Running tailscale up"
tailscale --socket=/tmp/tailscaled.sock up "${UP_ARGS}"

TS_IP=$(tailscale --socket=/tmp/tailscaled.sock ip -4)
TS_IP_B64=$(echo -n "${TS_IP}" | base64 -w 0)

# Technically can get the service ClusterIP through the <svc-name>_SERVICE_HOST variable
# but no idea how to do that in a sane way in pure Bash, so let's just get it from kube-dns
SVC_IP=$(echo ${SVC_NAME}.${KUBERNETES_NAMESPACE}.svc | cut -d" " -f1)

echo "Adding iptables rule for DNAT"
iptables -t nat -I PREROUTING -d "${TS_IP}" -j DNAT --to-destination "${SVC_IP}"

echo "Updating secret with Tailscale IP"
# patch secret with the tailscale ipv4 address
KUBERNETES_NAMESPACE=$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace)
kubectl patch secret "${TS_KUBE_SECRET}" --namespace "${KUBERNETES_NAMESPACE}" --type=json --patch="[{\"op\":\"replace\",\"path\":\"/data/ts-ip\",\"value\":\"${TS_IP_B64}\"}]"

wait ${PID}
