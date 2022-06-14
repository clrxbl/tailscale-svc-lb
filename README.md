# tailscale-svc-lb

[klipper-lb](https://github.com/k3s-io/klipper-lb) but Tailscale.
Basically does what [Tailscale's k8s examples](https://github.com/tailscale/tailscale/tree/main/docs/k8s) do but as a Kubernetes load balancer controller to automatically provision Tailscale IPs for internal Kubernetes LoadBalancer services.

[![asciicast](https://asciinema.org/a/smlS1PDekgvJBDuClsz9huMJy.svg)](https://asciinema.org/a/smlS1PDekgvJBDuClsz9huMJy)

## Installation

There's a Helm chart in the chart directory. There's no public Helm repository available (yet).
It deploys the controller & any svc-lb pods in the namespace where it's installed.

Once the controller is deployed, create a LoadBalancer service with the loadBalancerClass set to "svc-lb.tailscale.iptables.sh/lb".

There should be a DaemonSet created in the controller's namespace for the newly-created LoadBalancer service. View the logs of the leader-elected pod and click the login.tailscale.com link to authenticate. You only have to do this once per service.

This can be automated by creating a secret in the controller's namespace called `tailscale-svc-lb` with the key `ts-auth-key` and the value being your Tailscale's registration token.

## How it works

**On new LoadBalancer service:**
1. Look for LoadBalancer services with our loadbalancerclass
2. Look for nodes with the label `svc-lb.tailscale.iptables.sh/deploy=true`
3. Deploy a DaemonSet with the name: `ts-${SVC_NAME}` and our custom Docker image containing tailscaled.
4. Let the DaemonSet container run tailscaled, once IP is acquired, update tailscaled's secret with the Tailscale IP.
5. Retrieve IP from secret/configmap, update LoadBalancer service with ingress IP (Tailscale IP)


Each `tailscale-svc-lb-runtime` DaemonSet runs the `leader-elector` sidecar to automatically elect a leader using the Kubernetes leader election system.  `tailscaled` only works properly when ran on 1 pod at a time, hence this leader election system.

iptables DNAT is used to redirect incoming traffic to the service ClusterIP address, so `NET_ADMIN` capability is required & ipv4 forwarding.

**On LoadBalancer service deletion:**
1. Delete the DaemonSet
2. Delete the Secret/ConfigMap
3. Let Kubernetes delete the service
