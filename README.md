# tailscale-svc-lb

[klipper-lb](https://github.com/k3s-io/klipper-lb) but Tailscale.
Basically does what https://github.com/tailscale/tailscale/tree/main/docs/k8s does but as a load balancer controller to automatically provision Tailscale IPs for internal load balancers.


On new LoadBalancer service:
1. Look for LoadBalancer services with our loadbalancerclass
2. Look for nodes with the label svc-lb.tailscale.iptables.sh/deploy=true
3. Deploy a DaemonSet with the name: "ts-${SVC_NAME}" and our custom Docker image containing tailscaled.
4. Let the DaemonSet container run tailscaled, once IP is acquired, update tailscaled's secret with the Tailscale IP.
5. Retrieve IP from secret/configmap, update LoadBalancer service with ingress IP (Tailscale IP)


On LoadBalancer service deletion:
1. Delete the DaemonSet
2. Delete the Secret/ConfigMap
3. Let Kubernetes delete the service