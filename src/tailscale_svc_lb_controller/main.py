#!/usr/bin/env python3
import kopf
import logging
import kubernetes
import base64
import os

# Constants
CONTROLLER_PREFIX = "svc-lb.tailscale.iptables.sh"
CONTROLLER_NAMESPACE = os.getenv("CONTROLLER_NAMESPACE")
SECRET_NAME = "tailscale-svc-lb"
LOAD_BALANCER_CLASS = CONTROLLER_PREFIX + "/lb"
NODE_SELECTOR_LABEL = CONTROLLER_PREFIX + "/deploy"
SERVICE_NAME_LABEL = CONTROLLER_PREFIX + "/svc-name"
RESOURCE_PREFIX = "ts-"

TAILSCALE_RUNTIME_IMAGE = os.getenv("TAILSCALE_RUNTIME_IMAGE")
LEADER_ELECTOR_IMAGE = os.getenv("LEADER_ELECTOR_IMAGE")


def get_common_labels(service):
    """
    Get the labels common to all Tailscale services.
    """

    return {
        "app.kubernetes.io/name": "tailscale-svc-lb",
        "app.kubernetes.io/managed-by": "tailscale-svc-lb-controller",
        SERVICE_NAME_LABEL: service
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
        logging.error(e)


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.persistence.diffbase_storage = kopf.AnnotationsDiffBaseStorage(
        prefix=CONTROLLER_PREFIX,
        key="last-handled-configuration",
    )
    settings.persistence.finalizer = CONTROLLER_PREFIX + "/finalizer"
    settings.persistence.progress_storage = kopf.AnnotationsProgressStorage(prefix=CONTROLLER_PREFIX)


@kopf.on.create("services", field="spec.loadBalancerClass", value=LOAD_BALANCER_CLASS)
def create_svc_lb(spec, name, logger, **kwargs):
    """
    Create a service load balancer instance.
    """

    namespace = CONTROLLER_NAMESPACE
    logging.info(f"Creating svc-lb resources in namespace {namespace} for service {name}")

    common_labels = get_common_labels(name)

    # Create ServiceAccount
    k8s = kubernetes.client.CoreV1Api()
    k8s.create_namespaced_service_account(namespace=namespace, body=kubernetes.client.V1ServiceAccount(
        metadata=kubernetes.client.V1ObjectMeta(
            name=RESOURCE_PREFIX + name,
            labels=common_labels,
            namespace=namespace
        )
    ))

    # Create Role to manage secrets
    k8s = kubernetes.client.RbacAuthorizationV1Api()
    role = kubernetes.client.V1Role(
        metadata=kubernetes.client.V1ObjectMeta(
            name=RESOURCE_PREFIX + name,
            labels=common_labels,
            namespace=namespace,
        ),
        rules=[
            kubernetes.client.V1PolicyRule(
                api_groups=[""],
                resources=["secrets", "endpoints"],
                verbs=["create"]
            ),
            kubernetes.client.V1PolicyRule(
                api_groups=[""],
                resource_names=[f"{RESOURCE_PREFIX}{name}"],
                resources=["secrets", "endpoints"],
                verbs=["get", "update", "patch"]
            ),
            kubernetes.client.V1PolicyRule(
                api_groups=["coordination.k8s.io"],
                resource_names=[f"{RESOURCE_PREFIX}{name}"],
                resources=["leases"],
                verbs=["*"]
            )
        ],
    )
    k8s.create_namespaced_role(namespace, role)

    # Create RoleBinding
    role_binding = kubernetes.client.V1RoleBinding(
        metadata=kubernetes.client.V1ObjectMeta(
            name=RESOURCE_PREFIX + name,
            labels=common_labels,
            namespace=namespace,
        ),
        role_ref=kubernetes.client.V1RoleRef(
            api_group="rbac.authorization.k8s.io",
            kind="Role",
            name=RESOURCE_PREFIX + name,
        ),
        subjects=[
            kubernetes.client.V1Subject(
                kind="ServiceAccount",
                name=RESOURCE_PREFIX + name,
                namespace=namespace,
            ),
        ],
    )
    k8s.create_namespaced_role_binding(namespace, role_binding)

    # Create Secret
    k8s = kubernetes.client.CoreV1Api()
    secret = kubernetes.client.V1Secret(
        metadata=kubernetes.client.V1ObjectMeta(
            name=RESOURCE_PREFIX + name,
            labels=common_labels,
            namespace=namespace,
        ),
        type="Opaque",
        string_data={}
    )
    k8s.create_namespaced_secret(namespace, secret)

    # Create the DaemonSet
    k8s = kubernetes.client.AppsV1Api()
    k8s.create_namespaced_daemon_set(
        namespace=namespace,
        body=kubernetes.client.V1DaemonSet(
            metadata=kubernetes.client.V1ObjectMeta(
                name=RESOURCE_PREFIX + name,
                labels=common_labels
            ),
            spec=kubernetes.client.V1DaemonSetSpec(
                selector=kubernetes.client.V1LabelSelector(
                    match_labels=common_labels
                ),
                template=kubernetes.client.V1PodTemplateSpec(
                    metadata=kubernetes.client.V1ObjectMeta(
                        labels=common_labels
                    ),
                    spec=kubernetes.client.V1PodSpec(
                        service_account=RESOURCE_PREFIX + name,
                        service_account_name=RESOURCE_PREFIX + name,
                        node_selector={NODE_SELECTOR_LABEL: "true"},
                        containers=[
                            kubernetes.client.V1Container(
                                name="tailscale-svc-lb-runtime",
                                image=TAILSCALE_RUNTIME_IMAGE,
                                image_pull_policy="Always", # TODO: Return to IfNotPresent
                                env=[
                                    kubernetes.client.V1EnvVar(
                                        name="TS_KUBE_SECRET", value=RESOURCE_PREFIX + name
                                    ),
                                    kubernetes.client.V1EnvVar(
                                        name="SVC_NAME", value=name
                                    ),
                                    kubernetes.client.V1EnvVar(
                                        name="SVC_NAMESPACE", value=namespace
                                    ),
                                    kubernetes.client.V1EnvVar(
                                        name="TS_AUTH_KEY", value_from=kubernetes.client.V1EnvVarSource(
                                            secret_key_ref=kubernetes.client.V1SecretKeySelector(
                                                name=SECRET_NAME,
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
                                image=LEADER_ELECTOR_IMAGE,
                                image_pull_policy="IfNotPresent",
                                args=[f"--election={RESOURCE_PREFIX}{name}", f"--election-namespace={namespace}", "--http=0.0.0.0:4040"],
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
                ),
            ),
        ),
    )


@kopf.on.field("secrets", field="data.ts-ip")
def update_svc(body, namespace, **kwargs):
    """
    Update the LoadBalancer service status with the Tailscale IP.
    """

    # Get service name from svc-lb label
    service = body["metadata"]["labels"][SERVICE_NAME_LABEL]

    # Get Tailscale IP from the service's secret
    ip = base64.b64decode(body["data"]["ts-ip"]).decode("utf-8")

    logging.info(f"Updating LoadBalancer service in namespace {namespace} with Tailscale IP {ip}")

    update_service_status(namespace, service, ip)


@kopf.on.delete("services", field="spec.loadBalancerClass", value=LOAD_BALANCER_CLASS)
def delete_svc_lb(spec, name, logger, **kwargs):
    """
    Delete all created service load balancer resources.
    """

    namespace = CONTROLLER_NAMESPACE
    logging.info(f"Deleting svc-lb resources in namespace {namespace} for service {name}")

    k8s = kubernetes.client.AppsV1Api()
    # Delete all DaemonSets with svc-name label
    k8s.delete_collection_namespaced_daemon_set(
        namespace=namespace,
        label_selector=f"{SERVICE_NAME_LABEL}={name}"
    )

    # Delete RoleBinding with svc-name label
    k8s = kubernetes.client.RbacAuthorizationV1Api()
    k8s.delete_collection_namespaced_role_binding(
        namespace=namespace,
        label_selector=f"{SERVICE_NAME_LABEL}={name}"
    )

    # Delete Role with svc-name label
    k8s = kubernetes.client.RbacAuthorizationV1Api()
    k8s.delete_collection_namespaced_role(
        namespace=namespace,
        label_selector=f"{SERVICE_NAME_LABEL}={name}"
    )

    # Delete ServiceAccount with svc-name label
    k8s = kubernetes.client.CoreV1Api()
    k8s.delete_collection_namespaced_service_account(
        namespace=namespace,
        label_selector=f"{SERVICE_NAME_LABEL}={name}"
    )

    # Delete Secret with svc-name label
    k8s = kubernetes.client.CoreV1Api()
    k8s.delete_collection_namespaced_secret(
        namespace=namespace,
        label_selector=f"{SERVICE_NAME_LABEL}={name}"
    )

    # TODO: Automatically remove device from tailnet
