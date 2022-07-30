import kubernetes

from src.tailscale_svc_lb_controller import config
from src.tailscale_svc_lb_controller import helpers


class BaseResource:
    target_service_name = ""
    target_service_namespace = ""
    tailscale_proxy_namespace = ""

    # All resources that inherit this class need to implement the following methods
    def new(self): raise NotImplementedError

    def create(self): raise NotImplementedError

    def delete(self): raise NotImplementedError

    def get(self): raise NotImplementedError

    def reconcile(self): raise NotImplementedError

    def _generate_pod_template_spec(self) -> kubernetes.client.V1PodTemplateSpec:
        node_selector = None
        if config.NODE_SELECTOR_LABEL is not None:
            node_selector = {config.NODE_SELECTOR_LABEL: "true"}

        return kubernetes.client.V1PodTemplateSpec(
            metadata=kubernetes.client.V1ObjectMeta(
                labels=helpers.get_common_labels(self.target_service_name, self.target_service_namespace)
            ),
            spec=kubernetes.client.V1PodSpec(
                service_account=f"{config.RESOURCE_PREFIX}{self.target_service_name}",
                service_account_name=f"{config.RESOURCE_PREFIX}{self.target_service_name}",
                node_selector=node_selector,
                image_pull_secrets=helpers.get_image_pull_secrets(),
                init_containers=[
                    kubernetes.client.V1Container(
                        name="tailscale-svc-lb-init",
                        image=config.TS_PROXY_RUNTIME_IMAGE,
                        image_pull_policy=config.TS_PROXY_RUNTIME_IMAGE_PULL_POLICY,
                        command=['sh', '-c', 'sysctl -w net.ipv4.ip_forward=1'],
                        resources=kubernetes.client.V1ResourceRequirements(
                            requests={"cpu": config.TS_PROXY_RUNTIME_REQUEST_CPU,
                                      "memory": config.TS_PROXY_RUNTIME_REQUEST_MEM},
                            limits={"cpu": config.TS_PROXY_RUNTIME_LIMIT_CPU,
                                    "memory": config.TS_PROXY_RUNTIME_LIMIT_MEM}
                        ),
                        security_context=kubernetes.client.V1SecurityContext(
                            privileged=True,
                            capabilities=kubernetes.client.V1Capabilities(
                                add=[
                                    "NET_ADMIN"
                                ]
                            )
                        )
                    ),
                ],
                containers=[
                    kubernetes.client.V1Container(
                        name="tailscale-svc-lb-runtime",
                        image=config.TS_PROXY_RUNTIME_IMAGE,
                        image_pull_policy=config.TS_PROXY_RUNTIME_IMAGE_PULL_POLICY,
                        resources=kubernetes.client.V1ResourceRequirements(
                            requests={"cpu": config.TS_PROXY_RUNTIME_REQUEST_CPU,
                                      "memory": config.TS_PROXY_RUNTIME_REQUEST_MEM},
                            limits={"cpu": config.TS_PROXY_RUNTIME_LIMIT_CPU,
                                    "memory": config.TS_PROXY_RUNTIME_LIMIT_MEM}
                        ),
                        env=[
                            kubernetes.client.V1EnvVar(
                                name="TS_KUBE_SECRET", value=config.RESOURCE_PREFIX + self.target_service_name
                            ),
                            kubernetes.client.V1EnvVar(
                                name="SVC_NAME", value=self.target_service_name
                            ),
                            kubernetes.client.V1EnvVar(
                                name="SVC_NAMESPACE", value=self.target_service_namespace
                            ),
                            kubernetes.client.V1EnvVar(
                                name="TS_HOSTNAME",
                                value=helpers.get_hostname(self.target_service_name,
                                                           self.target_service_namespace)
                            ),
                            kubernetes.client.V1EnvVar(
                                name="TS_AUTH_KEY", value_from=kubernetes.client.V1EnvVarSource(
                                    secret_key_ref=kubernetes.client.V1SecretKeySelector(
                                        name=config.SECRET_NAME,
                                        key="ts-auth-key",
                                        optional=True,
                                    )
                                )
                            )
                        ],
                        lifecycle=kubernetes.client.V1Lifecycle(
                            pre_stop=kubernetes.client.V1LifecycleHandler(
                                _exec=kubernetes.client.V1ExecAction(
                                    command=["/stop.sh"]
                                )
                            )
                        ),
                        security_context=kubernetes.client.V1SecurityContext(
                            privileged=True,
                            capabilities=kubernetes.client.V1Capabilities(
                                add=[
                                    "NET_ADMIN"
                                ]
                            )
                        )
                    ),
                    kubernetes.client.V1Container(
                        name="leader-elector",
                        image=config.LEADER_ELECTOR_IMAGE,
                        image_pull_policy=config.LEADER_ELECTOR_IMAGE_PULL_POLICY,
                        resources=kubernetes.client.V1ResourceRequirements(
                            requests={"cpu": config.LEADER_ELECTOR_REQUEST_CPU,
                                      "memory": config.LEADER_ELECTOR_REQUEST_MEM},
                            limits={"cpu": config.LEADER_ELECTOR_LIMIT_CPU,
                                    "memory": config.LEADER_ELECTOR_LIMIT_MEM}
                        ),
                        args=[
                            f"--election={config.RESOURCE_PREFIX}{self.target_service_name}",
                            f"--election-namespace={self.tailscale_proxy_namespace}",
                            "--http=0.0.0.0:4040"
                        ],
                        lifecycle=kubernetes.client.V1Lifecycle(
                            pre_stop=kubernetes.client.V1LifecycleHandler(
                                _exec=kubernetes.client.V1ExecAction(
                                    command=["pkill", "-f", "server"]
                                )
                            )
                        )
                    )
                ],
            ),
        )
