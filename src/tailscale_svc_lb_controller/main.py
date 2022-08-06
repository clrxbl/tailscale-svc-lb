#!/usr/bin/env python3
import base64
import logging

import kopf

import config
from src.tailscale_svc_lb_controller import helpers
from tailscale_proxy import TailscaleProxyResource


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.persistence.diffbase_storage = kopf.AnnotationsDiffBaseStorage(
        prefix=config.CONTROLLER_PREFIX,
        key="last-handled-configuration",
    )
    settings.persistence.finalizer = config.CONTROLLER_PREFIX + "/finalizer"
    settings.persistence.progress_storage = kopf.AnnotationsProgressStorage(prefix=config.CONTROLLER_PREFIX)


@kopf.on.field("secrets", field="data.ts-ip")
def update_svc(body, namespace, **kwargs):
    """
    Update the LoadBalancer service status with the Tailscale IP.
    """

    # Get service name from svc-lb label
    service = body["metadata"]["labels"][config.SERVICE_NAME_LABEL]
    service_namespace = body["metadata"]["labels"][config.SERVICE_NAMESPACE_LABEL]

    # Get Tailscale IP from the service's secret
    ip = base64.b64decode(body["data"]["ts-ip"]).decode("utf-8")

    logging.info(f"Updating LoadBalancer service {config.TS_PROXY_NAMESPACE}/{service} with Tailscale IP {ip}")

    helpers.update_service_status(service_namespace, service, ip)


@kopf.on.delete("services", field="spec.loadBalancerClass", value=config.LOAD_BALANCER_CLASS)
def delete_svc_lb(spec, name, logger, **kwargs):
    """
    Delete all created service load balancer resources.
    """
    service_namespace = kwargs['meta']['namespace']
    ts = TailscaleProxyResource(
        target_service_name=name,
        target_service_namespace=service_namespace,
        tailscale_proxy_namespace=config.TS_PROXY_NAMESPACE,
        deployment_type=config.DEPLOYMENT_TYPE
    )
    logging.info(f"Deleting svc-lb resources in namespace {config.TS_PROXY_NAMESPACE}"
                 f" for service {service_namespace}/{name}")
    ts.delete()

    # TODO: Automatically remove device from tailnet
    #   In the meantime, using an Ephemeral key to register devices is a workaround


@kopf.timer('services', interval=10.0, field="spec.loadBalancerClass", value=config.LOAD_BALANCER_CLASS)
def create_svc_lb_timer(spec, **kwargs):
    ts = TailscaleProxyResource(
        target_service_name=kwargs['body']['metadata']['name'],
        target_service_namespace=kwargs['body']['metadata']['namespace'],
        tailscale_proxy_namespace=config.TS_PROXY_NAMESPACE,
        deployment_type=config.DEPLOYMENT_TYPE
    )
    ts.reconcile()
