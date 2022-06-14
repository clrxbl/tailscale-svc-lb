#!/bin/bash

set -x

tailscale --socket=/tmp/tailscaled.sock down
tailscaled --socket=/tmp/tailscaled.sock --cleanup
pkill -f tailscale