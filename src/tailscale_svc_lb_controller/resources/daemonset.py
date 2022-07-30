import kubernetes

from src.tailscale_svc_lb_controller import helpers, config
from src.tailscale_svc_lb_controller.resources.base import BaseResource


class DaemonSet(BaseResource):

    def __init__(self, target_service_name: str, target_service_namespace: str, namespace: str):
        self.target_service_name = target_service_name
        self.target_service_namespace = target_service_namespace
        self.tailscale_proxy_namespace = namespace

    def new(self) -> kubernetes.client.V1DaemonSet:
        """
        Returns the kubernetes.client.V1DaemonSet that runs the tailscale proxy instance
        """
        return kubernetes.client.V1DaemonSet(
            api_version="apps/v1",
            metadata=kubernetes.client.V1ObjectMeta(
                name=f"{config.RESOURCE_PREFIX}{self.target_service_name}",
                labels=helpers.get_common_labels(self.target_service_name, self.target_service_namespace)
            ),
            spec=kubernetes.client.V1DaemonSetSpec(
                selector=kubernetes.client.V1LabelSelector(
                    match_labels=helpers.get_common_labels(self.target_service_name, self.target_service_namespace)
                ),
                template=self._generate_pod_template_spec()
            ),
        )

    def create(self) -> kubernetes.client.V1DaemonSet:
        """
        Creates the DaemonSet that runs the Tailscale Proxy
        """
        k8s = kubernetes.client.AppsV1Api()
        deployment = self.new()

        return k8s.create_namespaced_daemon_set(
            namespace=self.tailscale_proxy_namespace,
            body=deployment
        )

    def delete(self) -> None:
        """
        Delete the DaemonSet deployed as part of a proxy instance, if it exists.
        """
        k8s = kubernetes.client.AppsV1Api()
        # Delete all DaemonSets with svc-name label
        try:
            k8s.delete_collection_namespaced_daemon_set(
                namespace=self.tailscale_proxy_namespace,
                label_selector=f"{config.SERVICE_NAME_LABEL}={self.target_service_name}"
            )
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 404:
                return None
            raise e

    def get(self) -> kubernetes.client.V1DaemonSet | None:
        """
        Fetches the current DaemonSet that should have been deployed as part of the proxy instance
        """
        k8s = kubernetes.client.AppsV1Api()
        try:
            return k8s.read_namespaced_daemon_set(
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
