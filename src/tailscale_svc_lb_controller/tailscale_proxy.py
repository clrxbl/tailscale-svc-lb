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
        self.target_service_name = target_service_name
        self.target_service_namespace = target_service_namespace
        self.tailscale_proxy_namespace = tailscale_proxy_namespace
        self.deployment_type = deployment_type

    def create(self):
        ServiceAccount(self.target_service_name, self.target_service_namespace, self.tailscale_proxy_namespace).create()
        Role(self.target_service_name, self.target_service_namespace, self.tailscale_proxy_namespace).create()
        RoleBinding(self.target_service_name, self.target_service_namespace, self.tailscale_proxy_namespace).create()
        Secret(self.target_service_name, self.target_service_namespace, self.tailscale_proxy_namespace).create()
        if self.deployment_type.lower() == "daemonset":
            DaemonSet(self.target_service_name, self.target_service_namespace, self.tailscale_proxy_namespace).create()
        elif self.deployment_type.lower() == "deployment":
            Deployment(self.target_service_name, self.target_service_namespace, self.tailscale_proxy_namespace).create()

    def delete(self):
        if self.deployment_type.lower() == "daemonset":
            DaemonSet(self.target_service_name, self.target_service_namespace, self.tailscale_proxy_namespace).delete()
        elif self.deployment_type.lower() == "deployment":
            Deployment(self.target_service_name, self.target_service_namespace, self.tailscale_proxy_namespace).delete()
        Secret(self.target_service_name, self.target_service_namespace, self.tailscale_proxy_namespace).delete()
        RoleBinding(self.target_service_name, self.target_service_namespace, self.tailscale_proxy_namespace).delete()
        Role(self.target_service_name, self.target_service_namespace, self.tailscale_proxy_namespace).delete()
        ServiceAccount(self.target_service_name, self.target_service_namespace, self.tailscale_proxy_namespace).delete()

    def reconcile(self):
        ServiceAccount(self.target_service_name, self.target_service_namespace,
                       self.tailscale_proxy_namespace).reconcile()
        Role(self.target_service_name, self.target_service_namespace, self.tailscale_proxy_namespace).reconcile()
        RoleBinding(self.target_service_name, self.target_service_namespace, self.tailscale_proxy_namespace).reconcile()
        Secret(self.target_service_name, self.target_service_namespace, self.tailscale_proxy_namespace).reconcile()
        if self.deployment_type.lower() == "daemonset":
            DaemonSet(self.target_service_name, self.target_service_namespace,
                      self.tailscale_proxy_namespace).reconcile()
        elif self.deployment_type.lower() == "deployment":
            Deployment(self.target_service_name, self.target_service_namespace,
                       self.tailscale_proxy_namespace).reconcile()
