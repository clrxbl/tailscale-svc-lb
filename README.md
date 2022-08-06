# tailscale-svc-lb

[klipper-lb](https://github.com/k3s-io/klipper-lb) but Tailscale.
Basically does what [Tailscale's k8s examples](https://github.com/tailscale/tailscale/tree/main/docs/k8s) do but as a Kubernetes load balancer controller to automatically provision Tailscale IPs for internal Kubernetes LoadBalancer services.

[![asciicast](https://asciinema.org/a/smlS1PDekgvJBDuClsz9huMJy.svg)](https://asciinema.org/a/smlS1PDekgvJBDuClsz9huMJy)

## Installation

There's a Helm chart in the chart directory. There's no public Helm repository available (yet).
It deploys the controller & any svc-lb pods in the namespace where it's installed.

Once the controller is deployed, create a LoadBalancer service with the loadBalancerClass set to "svc-lb.tailscale.iptables.sh/lb".

There should be a Deployment (or DaemonSet) created in the controller's namespace for the newly-created LoadBalancer service. View the logs of the leader-elected pod and click the login.tailscale.com link to authenticate. You only have to do this once per service.

This can be automated by creating a secret in the controller's namespace called `tailscale-svc-lb` with the key `ts-auth-key` and the value being your Tailscale's registration token.

## Configuration Variables

All configuration options are supplied using Environment Variables

| Variable                             | Description                                                                                                                        | Default                                        |
|--------------------------------------|------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------|
 | `RESOURCE_PREFIX`                    | Prefix to prepend to the service name when creating proxy resources                                                                | `ts-`                                          |
| `SECRET_NAME`                        | Name of the secret that the `ts-auth-key` value should be used from                                                                | `tailscale-svc-lb`                             |
| `LOAD_BALANCER_CLASS`                | LoadBalancerClass that this controller will implement                                                                              | `svc-lb.tailscale.iptables.sh/lb`              |
| `NODE_SELECTOR_LABEL`                | Label to use when selecting nodes to run Tailscale on. The value of this label should be `true`                                    | None                                           |
| `IMAGE_PULL_SECRETS`                 | A semi-colon seperated list of secret names to use as the `imagePullSecrets` for the Tailscale Proxy                               | None                                           |
| `DEPLOYMENT_TYPE`                    | The type of deployment to use for the Tailscale Proxy. Can be one of: `Deployment`, `DaemonSet`                                    | `Deployment`                                   |
| `TS_PROXY_NAMESPACE`                 | Namespace all of the Tailscale Proxies will be created in                                                                          | `default`                                      |
| `TS_PROXY_REPLICA_COUNT`             | The number of replicas to deploy for each Tailscale Proxy instance. Only used if `DEPLOYMENT_TYPE` is `Deployment`                 | `1`                                            |
| `TS_PROXY_RUNTIME_IMAGE`             | Image to use as the Tailscale Proxy Runtime container                                                                              | `clrxbl/tailscale-svc-lb-runtime:latest`       |
| `TS_PROXY_RUNTIME_IMAGE_PULL_POLICY` | ImagePullPolicy to use for the Tailscale Proxy Runtime container                                                                   | `IfNotPresent`                                 |
| `TS_PROXY_RUNTIME_REQUEST_CPU`       | CPU Request for the Tailscale Proxy Runtime container                                                                              | None                                           |
| `TS_PROXY_RUNTIME_REQUEST_MEM`       | Memory Request for the Tailscale Proxy Runtime container                                                                           | None                                           |
| `TS_PROXY_RUNTIME_LIMIT_CPU`         | CPU Limit for the Tailscale Proxy Runtime container                                                                                | None                                           |
| `TS_PROXY_RUNTIME_LIMIT_MEM`         | Memory Limit for the Tailscale Proxy Runtime container                                                                             | None                                           |
| `LEADER_ELECTOR_IMAGE`               | Image to use as the Leader Elector container                                                                                       | `gcr.io/google_containers/leader-elector: 0.5` |
| `LEADER_ELECTOR_IMAGE_PULL_POLICY`   | ImagePullPolicy to use for the Leader Elector container                                                                            | `IfNotPresent`                                 |
| `LEADER_ELECTOR_REQUEST_CPU`         | CPU Request for the Leader Elector container                                                                                       | None                                           |
| `LEADER_ELECTOR_REQUEST_MEM`         | Memory Request for the Leader Elector container                                                                                    | None                                           |
| `LEADER_ELECTOR_LIMIT_CPU`           | CPU Limit for the Leader Elector container                                                                                         | None                                           |
| `LEADER_ELECTOR_LIMIT_MEM`           | Memory Limit for the Leader Elector container                                                                                      | None                                           |
| `TS_HOSTNAME_FROM_SERVICE`           | If set to `true`, the Hostname of the Tailscale Proxy will be generated from the namespace and service name of the proxied service | `false`                                        |
| `TS_HOSTNAME_FROM_SERVICE_SUFFIX`    | An optional hostname suffix to add to automatically generated Hostnames. Only applies if `TS_HOSTNAME_FROM_SERVICE` is `true`      | None                                           |

## How it works

**On new LoadBalancer service:**
1. Look for LoadBalancer services with our loadBalancerClass (Default: `svc-lb.tailscale.iptables.sh/lb`)
2. Look for nodes with our nodeSelectorLabel (Default: `svc-lb.tailscale.iptables.sh/deploy`) with the value `true`
3. Deploy a Deployment or DaemonSet with the name: `${RESOURCE_PREFIX}${SVC_NAME}` and our custom Docker image containing tailscaled.
4. Let the Deployment or DaemonSet run tailscaled, once IP is acquired, update tailscaled's secret with the Tailscale IP.
5. Retrieve IP from secret/configmap, update LoadBalancer service with ingress IP (Tailscale IP)

Each `tailscale-svc-lb-runtime` DaemonSet/Deployment runs the `leader-elector` sidecar to automatically elect a leader using the Kubernetes leader election system.  `tailscaled` only works properly when ran on 1 pod at a time, hence this leader election system.

iptables DNAT is used to redirect incoming traffic to the service ClusterIP address, so `NET_ADMIN` capability is required & ipv4 forwarding.

**On LoadBalancer service deletion:**
1. Delete the DaemonSet
2. Delete the Secret/ConfigMap
3. Let Kubernetes delete the service

**Every 15 Seconds, after an initial 30 second idle time:**
1. Iterate all LoadBalancer services with our loadBalancerClass (Default: `svc-lb.tailscale.iptables.sh/lb`)
2. Reconcile the state of the relevant `${RESOURCE_PREFIX}${SVC_NAME` resources
3. If any resources are missing, create the Deployment/DaemonSet/Role/RoleBindings/ServiceAccount as necessary