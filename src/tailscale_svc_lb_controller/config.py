#!/usr/bin/env python3
import logging
import re
import sys
from os import environ as env

# -- Constants
CONTROLLER_PREFIX = "svc-lb.tailscale.iptables.sh"
SERVICE_NAME_LABEL = CONTROLLER_PREFIX + "/svc-name"
SERVICE_NAMESPACE_LABEL = CONTROLLER_PREFIX + "/svc-namespace"

# -- Proxy Deployment Configuration
RESOURCE_PREFIX = env.get("RESOURCE_PREFIX", "ts-")
SECRET_NAME = env.get("SECRET_NAME", "tailscale-svc-lb")
# LoadBalancerClass this instance of Tailscale Proxy will implement
LOAD_BALANCER_CLASS = env.get("LOAD_BALANCER_CLASS", CONTROLLER_PREFIX + "/lb")
# Label to use when selecting nodes for the Tailscale Proxy to run on. The value of this label should be 'true'
NODE_SELECTOR_LABEL = env.get("TS_PROXY_NODE_SELECTOR_LABEL", None)

# A semi-colon seperated string containing the names of any secrets that should be used
# when pulling images. Secret must already exist and be present in the TS_PROXY_NAMESPACE
IMAGE_PULL_SECRETS = env.get("IMAGE_PULL_SECRETS", "")
if not re.match(r"^([a-z]|-|\d|;)*$", IMAGE_PULL_SECRETS):
    logging.error("IMAGE_PULL_SECRETS invalid. Should be a semi-colon seperated list of"
                  "secret names.")
    sys.exit(1)

# Type of deployment to use for the Tailscale Proxy instances
DEPLOYMENT_TYPE = env.get("DEPLOYMENT_TYPE", "DaemonSet")
if DEPLOYMENT_TYPE not in ["DaemonSet", "Deployment"]:
    logging.error("DEPLOYMENT_TYPE invalid. Valid options are 'DaemonSet', 'Deployment'")
    sys.exit(1)

# Tailscale Proxy Runtime Namepace. All Tailscale Proxies will be created in this namespace.
TS_PROXY_NAMESPACE = env.get("TS_PROXY_NAMESPACE", "default")

# If TS_PROXY_DEPLOYMENT_TYPE is 'Deployment', this dictates the number of replicas. No effect otherwise.
try:
    TS_PROXY_REPLICA_COUNT = int(env.get("TS_PROXY_REPLICA_COUNT", "2"))
except Exception:
    logging.error("TS_PROXY_REPLICA_COUNT value invalid. Should be an integer above 0.")
    sys.exit(1)

# Tailscale Proxy Runtime Container Image
TS_PROXY_RUNTIME_IMAGE = env.get("TS_PROXY_RUNTIME_IMAGE", "clrxbl/tailscale-svc-lb-runtime:latest")

# Tailscale Proxy Runtime Container ImagePullPolicy
TS_PROXY_RUNTIME_IMAGE_PULL_POLICY = env.get("TS_PROXY_RUNTIME_IMAGE_PULL_POLICY", "IfNotPresent")
if TS_PROXY_RUNTIME_IMAGE_PULL_POLICY not in ["Always", "IfNotPresent", "Never"]:
    logging.error(
        "TS_PROXY_RUNTIME_IMAGE_PULL_POLICY invalid. Valid options are 'Always', 'IfNotPresent', and "
        "'Never'")
    sys.exit(1)

# Tailscale Proxy Runtime Container Requests/Limits
TS_PROXY_RUNTIME_REQUEST_CPU = env.get("TS_PROXY_RUNTIME_REQUEST_CPU", None)
TS_PROXY_RUNTIME_REQUEST_MEM = env.get("TS_PROXY_RUNTIME_REQUEST_MEM", None)
TS_PROXY_RUNTIME_LIMIT_CPU = env.get("TS_PROXY_RUNTIME_LIMIT_CPU", None)
TS_PROXY_RUNTIME_LIMIT_MEM = env.get("TS_PROXY_RUNTIME_LIMIT_MEM", None)

# The docker image that will be run as the Leader Elector
LEADER_ELECTOR_IMAGE = env.get("LEADER_ELECTOR_IMAGE", "gcr.io/google_containers/leader-elector:0.5")

# ImagePullPolicy to use when retrieving LEADER_ELECTOR_IMAGE
LEADER_ELECTOR_IMAGE_PULL_POLICY = env.get("LEADER_ELECTOR_IMAGE_PULL_POLICY", "IfNotPresent")
if LEADER_ELECTOR_IMAGE_PULL_POLICY not in ["Always", "IfNotPresent", "Never"]:
    logging.error(
        "LEADER_ELECTOR_IMAGE_PULL_POLICY invalid. Valid options are 'Always', 'IfNotPresent', and "
        "'Never'")
    sys.exit(1)

# Tailscale Proxy Runtime Container Requests/Limits
LEADER_ELECTOR_REQUEST_CPU = env.get("LEADER_ELECTOR_REQUEST_CPU", None)
LEADER_ELECTOR_REQUEST_MEM = env.get("LEADER_ELECTOR_REQUEST_MEM", None)
LEADER_ELECTOR_LIMIT_CPU = env.get("LEADER_ELECTOR_LIMIT_CPU", None)
LEADER_ELECTOR_LIMIT_MEM = env.get("LEADER_ELECTOR_LIMIT_MEM", None)

# -- Tailscale Configuration
#
# Automatically generate a hostname based on the target service name and namespace.
#   Example: ts-kuard.default
TS_HOSTNAME_FROM_SERVICE = env.get("TS_HOSTNAME_FROM_SERVICE", "false")
if TS_HOSTNAME_FROM_SERVICE not in ["true", "false"]:
    logging.error("TS_HOSTNAME_FROM_SERVICE valid options are 'true', 'false'")
    sys.exit(1)

# An optional suffix to append to the automatically generated hostname. Only applies if TAILSCALE_HOSTNAME_FROM_SERVICE
# has been set to "true".
#   Example: ts-kuard.default.suffix
TS_HOSTNAME_FROM_SERVICE_SUFFIX = env.get("TS_HOSTNAME_FROM_SERVICE_SUFFIX", "")
