import logging

import kubernetes

from src.tailscale_svc_lb_controller import helpers, config
from src.tailscale_svc_lb_controller.resources.base import BaseResource


class RoleBinding(BaseResource):

    def __init__(self, target_service_name: str, target_service_namespace: str, namespace: str):
        self.target_service_name = target_service_name
        self.target_service_namespace = target_service_namespace
        self.tailscale_proxy_namespace = namespace

    def new(self) -> kubernetes.client.V1RoleBinding:
        """
        Returns the kubernetes.client.V1RoleBinding used for a Tailscale Proxy instance
        """
        return kubernetes.client.V1RoleBinding(
            metadata=kubernetes.client.V1ObjectMeta(
                name=f"{config.RESOURCE_PREFIX}{self.target_service_name}",
                labels=helpers.get_common_labels(self.target_service_name, self.target_service_namespace),
                namespace=self.tailscale_proxy_namespace,
            ),
            role_ref=kubernetes.client.V1RoleRef(
                api_group="rbac.authorization.k8s.io",
                kind="Role",
                name=f"{config.RESOURCE_PREFIX}{self.target_service_name}",
            ),
            subjects=[
                kubernetes.client.V1Subject(
                    kind="ServiceAccount",
                    name=f"{config.RESOURCE_PREFIX}{self.target_service_name}",
                    namespace=self.tailscale_proxy_namespace,
                ),
            ],
        )

    def create(self) -> kubernetes.client.V1RoleBinding:
        """
        Creates the RoleBinding necessary to run the Tailscale Proxy
        """
        k8s = kubernetes.client.RbacAuthorizationV1Api()
        return k8s.create_namespaced_role_binding(
            namespace=self.tailscale_proxy_namespace,
            body=self.new()
        )

    def delete(self) -> None:
        """
        Delete the RoleBinding deployed as part of a proxy instance
        """
        k8s = kubernetes.client.RbacAuthorizationV1Api()
        try:
            k8s.delete_collection_namespaced_role_binding(
                namespace=self.tailscale_proxy_namespace,
                label_selector=f"{config.SERVICE_NAME_LABEL}={self.target_service_name}"
            )
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 404:
                logging.error(e)
                return None
            raise e

    def get(self) -> kubernetes.client.V1RoleBinding | None:
        """
        Fetches the current RoleBinding that should have been deployed as part of the proxy instance
        """
        k8s = kubernetes.client.RbacAuthorizationV1Api()
        try:
            return k8s.read_namespaced_role_binding(
                namespace=self.target_service_namespace,
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
