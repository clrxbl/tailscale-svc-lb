FROM tailscale/tailscale:latest
ADD https://dl.k8s.io/release/v1.24.1/bin/linux/amd64/kubectl /usr/local/bin/kubectl
RUN apk add --no-cache haproxy jq curl bash && chmod +x /usr/local/bin/kubectl
ADD *.sh /
CMD "/run.sh"
