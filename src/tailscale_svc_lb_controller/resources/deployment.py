import kubernetes

from src.tailscale_svc_lb_controller import helpers, config
from src.tailscale_svc_lb_controller.resources.base import BaseResource


class Deployment(BaseResource):

    def new(self) -> kubernetes.client.V1Deployment:
        """
        Returns the kubernetes.client.V1Deployment that runs the tailscale proxy instance
        """
        return kubernetes.client.V1Deployment(
            api_version="apps/v1",
            metadata=kubernetes.client.V1ObjectMeta(
                name=f"{config.RESOURCE_PREFIX}{self.target_service_name}",
                labels=helpers.get_common_labels(self.target_service_name, self.target_service_namespace)
            ),
            spec=kubernetes.client.V1DeploymentSpec(
                selector=kubernetes.client.V1LabelSelector(
                    match_labels=helpers.get_common_labels(self.target_service_name, self.target_service_namespace)
                ),
                replicas=config.TS_PROXY_REPLICA_COUNT,
                template=self._generate_pod_template_spec()
            ),
        )

    def create(self) -> kubernetes.client.V1Deployment:
        """
        Creates the Deployment that runs the Tailscale Proxy
        """
        k8s = kubernetes.client.AppsV1Api()
        deployment = self.new()
        return k8s.replace_namespaced_deployment(
            namespace=self.tailscale_proxy_namespace,
            body=deployment
        )

    def delete(self) -> None:
        """
        Delete the Deployment deployed as part of a proxy instance
        """
        k8s = kubernetes.client.AppsV1Api()
        # Delete all Deployments with svc-name label
        with(helpers.ignore_k8s_statuses(404)):
            k8s.delete_collection_namespaced_deployment(
                namespace=self.tailscale_proxy_namespace,
                label_selector=f"{config.SERVICE_NAME_LABEL}={self.target_service_name}"
            )

    def get(self) -> kubernetes.client.V1Deployment | None:
        """
        Fetches the current Deployment that should have been deployed as part of the proxy instance
        """
        k8s = kubernetes.client.AppsV1Api()
        with(helpers.ignore_k8s_statuses(404)):
            return k8s.read_namespaced_deployment(
                namespace=self.tailscale_proxy_namespace,
                name=f"{config.RESOURCE_PREFIX}{self.target_service_name}"
            )