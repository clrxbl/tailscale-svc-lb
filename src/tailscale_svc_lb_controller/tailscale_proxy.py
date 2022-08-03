from src.tailscale_svc_lb_controller.resources.daemonset import DaemonSet
from src.tailscale_svc_lb_controller.resources.deployment import Deployment
from src.tailscale_svc_lb_controller.resources.role import Role
from src.tailscale_svc_lb_controller.resources.role_binding import RoleBinding
from src.tailscale_svc_lb_controller.resources.secret import Secret
from src.tailscale_svc_lb_controller.resources.service_account import ServiceAccount


class TailscaleProxyResource:
    """
    Class to handle adding/fetching/deleting TailScale proxy kube resources
    """
    target_service_name = ""
    tailscale_proxy_namespace = ""
    target_service_namespace = ""
    deployment_type = ""

    def __init__(self, target_service_name: str, target_service_namespace: str,
                 tailscale_proxy_namespace: str, deployment_type: str):
        """
            target_service_name: Name of the target Service this Proxy Instance should direct traffic to
            target_service_namespace: Namespace of the target Service this Proxy Instance should direct traffic to
            tailscale_proxy_namespace: Namespace that the Tailscale Proxy resources will be created in
        """
        self.resources = [
            ServiceAccount(target_service_name, target_service_namespace, tailscale_proxy_namespace),
            Role(target_service_name, target_service_namespace, tailscale_proxy_namespace),
            RoleBinding(target_service_name, target_service_namespace, tailscale_proxy_namespace),
            Secret(target_service_name, target_service_namespace, tailscale_proxy_namespace),
            self.__get_deployment_class(deployment_type)(target_service_name, target_service_namespace, tailscale_proxy_namespace),
        ]

    @staticmethod
    def __get_deployment_class(deployment_type: str) -> Deployment | DaemonSet:
        match deployment_type.lower():
            case "daemonset":
                return DaemonSet
            case "deployment":
                return Deployment
            case _:
                raise ValueError(f"Invalid value for {deployment_type=}")

    def create(self):
        for resource in self.resources:
            resource.create()

    def delete(self):
        # Delete resources in reverse
        for resource in self.resources[::-1]:
            resource.delete()

    def reconcile(self):
        for resource in self.resources:
            resource.reconcile()