import kubernetes

from src.tailscale_svc_lb_controller import helpers, config
from src.tailscale_svc_lb_controller.resources.base import BaseResource


class Role(BaseResource):

    def __init__(self, target_service_name: str, target_service_namespace: str, namespace: str):
        self.target_service_name = target_service_name
        self.target_service_namespace = target_service_namespace
        self.tailscale_proxy_namespace = namespace

    def new(self) -> kubernetes.client.V1Role:
        """
        Returns the kubernetes.client.V1Role that
        """
        return kubernetes.client.V1Role(
            metadata=kubernetes.client.V1ObjectMeta(
                name=f"{config.RESOURCE_PREFIX}{self.target_service_name}",
                labels=helpers.get_common_labels(self.target_service_name, self.target_service_namespace),
                namespace=self.tailscale_proxy_namespace,
            ),
            rules=[
                kubernetes.client.V1PolicyRule(
                    api_groups=[""],
                    resources=["secrets", "endpoints"],
                    verbs=["create"]
                ),
                kubernetes.client.V1PolicyRule(
                    api_groups=[""],
                    resource_names=[f"{config.RESOURCE_PREFIX}{self.target_service_name}"],
                    resources=["secrets", "endpoints"],
                    verbs=["get", "update", "patch"]
                ),
                kubernetes.client.V1PolicyRule(
                    api_groups=["coordination.k8s.io"],
                    resource_names=[f"{config.RESOURCE_PREFIX}{self.target_service_name}"],
                    resources=["leases"],
                    verbs=["*"]
                )
            ],
        )

    def create(self) -> kubernetes.client.V1Role:
        """
        Creates the Role necessary to run the Tailscale Proxy
        """
        k8s = kubernetes.client.RbacAuthorizationV1Api()
        return k8s.create_namespaced_role(
            namespace=self.tailscale_proxy_namespace,
            body=self.new()
        )

    def delete(self) -> None:
        """
        Delete the Role deployed as part of a proxy instance
        """
        k8s = kubernetes.client.RbacAuthorizationV1Api()
        try:
            k8s.delete_collection_namespaced_role(
                namespace=self.tailscale_proxy_namespace,
                label_selector=f"{config.SERVICE_NAME_LABEL}={self.target_service_name}"
            )
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 404:
                return None
            raise e

    def get(self) -> kubernetes.client.V1Role | None:
        """
        Fetches the current Role that should have been deployed as part of the proxy instance
        """
        k8s = kubernetes.client.RbacAuthorizationV1Api()
        try:
            return k8s.read_namespaced_role(
                namespace=self.tailscale_proxy_namespace,
                name=f"{config.RESOURCE_PREFIX}{self.target_service_name}"
            )
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 404:
                return None
            else:
                raise e

    def reconcile(self):
        """
        Creates the resource if it doesn't already exist
        """
        existing = self.get()
        if existing is None:
            self.create()
