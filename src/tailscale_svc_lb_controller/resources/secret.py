import kubernetes

from src.tailscale_svc_lb_controller import helpers, config
from src.tailscale_svc_lb_controller.resources.base import BaseResource


class Secret(BaseResource):

    def new(self) -> kubernetes.client.V1Secret:
        """
        Returns the kubernetes.client.V1Secret required for the Tailscale Proxy
        """
        return kubernetes.client.V1Secret(
            metadata=kubernetes.client.V1ObjectMeta(
                name=f"{config.RESOURCE_PREFIX}{self.target_service_name}",
                labels=helpers.get_common_labels(self.target_service_name, self.target_service_namespace),
                namespace=self.tailscale_proxy_namespace,
            ),
            type="Opaque",
            string_data={}
        )

    def create(self) -> kubernetes.client.V1Secret:
        """
        Creates the Secret necessary to run the Tailscale Proxy
        """
        k8s = kubernetes.client.CoreV1Api()
        return k8s.create_namespaced_secret(
            namespace=self.tailscale_proxy_namespace,
            body=self.new()
        )

    def delete(self) -> None:
        """
        Delete the Secret deployed as part of a proxy instance
        """
        k8s = kubernetes.client.CoreV1Api()
        with(helpers.ignore_k8s_statuses(404)):
            k8s.delete_collection_namespaced_secret(
                namespace=self.tailscale_proxy_namespace,
                label_selector=f"{config.SERVICE_NAME_LABEL}={self.target_service_name}"
            )

    def get(self) -> kubernetes.client.V1Secret | None:
        """
        Fetches the current Secret that should have been deployed as part of the proxy instance
        """
        k8s = kubernetes.client.CoreV1Api()
        with(helpers.ignore_k8s_statuses(404)):
            return k8s.read_namespaced_secret(
                namespace=self.tailscale_proxy_namespace,
                name=f"{config.RESOURCE_PREFIX}{self.target_service_name}"
            )