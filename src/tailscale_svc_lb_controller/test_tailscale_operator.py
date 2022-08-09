import logging
import os
import random
import string
import time

import kubernetes.client
import yaml
from kopf.testing import KopfRunner
from kubernetes import client, config

import config as operator_config


def test_operator():
    ts_auth_key = os.getenv("TS_AUTH_KEY")
    if ts_auth_key is None:
        raise Exception("A Tailscale Auth Key must be supplied via the TS_AUTH_KEY env variable")

    print("Configuring Tailscale Auth Key Secret...")

    # Create a secret in the namespace controller to automatically authenticate against Tailscale
    config.load_config()
    k8s_api = client.CoreV1Api()
    rbac_api = client.RbacAuthorizationV1Api()
    app_api = client.AppsV1Api()

    k8s_api.create_namespaced_secret(operator_config.TS_PROXY_NAMESPACE, kubernetes.client.V1Secret(
        metadata=kubernetes.client.V1ObjectMeta(
            name=operator_config.SECRET_NAME,
            namespace=operator_config.TS_PROXY_NAMESPACE,
        ),
        type="Opaque",
        string_data={
            'ts-auth-key': ts_auth_key
        }
    ))

    print("Starting operator...")
    with KopfRunner(['run', '-A', '--verbose', 'main.py']) as runner:
        # Create a namespace to use for deploying example resources
        testing_namespace_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        logging.info(f"Creating namespace {testing_namespace_name} for example resources")
        k8s_api.create_namespace(kubernetes.client.V1Namespace(
            metadata=kubernetes.client.V1ObjectMeta(
                name=testing_namespace_name,
            )
        ))
        try:
            with open(os.path.join(os.path.dirname(__file__), 'examples', 'pod.yaml')) as file:
                pod = yaml.load(file, Loader=yaml.FullLoader)
                k8s_api.create_namespaced_pod(testing_namespace_name, pod)
            with open(os.path.join(os.path.dirname(__file__), 'examples', 'service.yaml')) as file:
                service = yaml.load(file, Loader=yaml.FullLoader)
                k8s_api.create_namespaced_service(testing_namespace_name, service)

            # Give it some time to create the tailscale proxy resources
            time.sleep(20)

            secret = k8s_api.read_namespaced_secret('ts-kuard', operator_config.TS_PROXY_NAMESPACE)
            assert (secret is not None)
            service_account = k8s_api.read_namespaced_service_account('ts-kuard', operator_config.TS_PROXY_NAMESPACE)
            assert (service_account is not None)
            role = rbac_api.read_namespaced_role('ts-kuard', operator_config.TS_PROXY_NAMESPACE)
            assert (role is not None)
            role_binding = rbac_api.read_namespaced_role_binding('ts-kuard', operator_config.TS_PROXY_NAMESPACE)
            assert (role_binding is not None)
            deployment = app_api.read_namespaced_deployment('ts-kuard', operator_config.TS_PROXY_NAMESPACE)
            assert (deployment is not None)
        except Exception as e:
            print(e)
        finally:
            k8s_api.delete_namespaced_secret(
                namespace=operator_config.TS_PROXY_NAMESPACE,
                name=operator_config.SECRET_NAME
            )
            k8s_api.delete_namespace(testing_namespace_name)

            # Give the operator time to cleanup any resources it created
            time.sleep(15)

    print(runner.output)
    assert runner.exit_code == 0
    assert runner.exception is None
    assert "Exception" not in runner.output
    assert "Error" not in runner.output


test_operator()
