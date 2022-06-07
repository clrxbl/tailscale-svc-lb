#!/bin/bash

tailscale --socket=/var/run/tailscale/tailscaled.sock down
tailscaled --socket=/var/run/tailscale/tailscaled.sock --cleanup
pkill -f tailscale