import logging

import kubernetes

import config


def get_common_labels(service, namespace):
    """
    Get the labels common to all resources managed by this operator.
    """

    return {
        "app.kubernetes.io/name": "tailscale-svc-lb",
        "app.kubernetes.io/managed-by": "tailscale-svc-lb-controller",
        config.SERVICE_NAME_LABEL: service,
        config.SERVICE_NAMESPACE_LABEL: namespace
    }


def update_service_status(namespace, service, ip):
    """
    Update the status of the service to reflect the service Tailscale IP.
    """

    try:
        # Get the service
        k8s = kubernetes.client.CoreV1Api()
        service_object = k8s.read_namespaced_service(name=service, namespace=namespace)

        # Update the status
        service_object.status.load_balancer.ingress = [
            kubernetes.client.V1LoadBalancerIngress(ip=ip)
        ]

        # Patch the service with the new status
        k8s.patch_namespaced_service_status(name=service, namespace=namespace, body=service_object)
    except Exception as e:
        raise e


def get_hostname(target_service_name: str, target_service_namespace: str) -> str:
    """
    Generates the hostname to use for the tailscale client.

    If config.TS_HOSTNAME_FROM_SERVICE is set to "true", the hostname will be automatically generated based on the
    supplied target service name, and namespace.

    While using config.TS_HOSTNAME_FROM_SERVICE, an optional domain suffix can be supplied by setting the
    config.TS_HOSTNAME_FROM_SERVICE_SUFFIX constant.

    If no configuration values are set, this will be left unconfigured and the Tailscale hostname will default to
    the pod name.
    """
    if config.TS_HOSTNAME_FROM_SERVICE == "true":
        if config.TS_HOSTNAME_FROM_SERVICE_SUFFIX != "":
            return f'{target_service_name}-{target_service_namespace}-{config.TS_HOSTNAME_FROM_SERVICE_SUFFIX}'
        else:
            return f'{target_service_name}-{target_service_namespace}'

    return ""


def get_image_pull_secrets() -> [str]:
    """
    Generates the imagePullSecrets to use, based on the semi-colon seperated string
    config.IMAGE_PULL_SECRETS.
    """
    if config.IMAGE_PULL_SECRETS is not None:
        logging.debug(f"Image Pull Secrets: {config.IMAGE_PULL_SECRETS}")
        retval = []
        secrets = config.IMAGE_PULL_SECRETS.split(";")
        for secret in secrets:
            retval.append(kubernetes.client.V1LocalObjectReference(name=secret))
        return retval
    return []
