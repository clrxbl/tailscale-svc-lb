

REPOSITORY=clrxbl/tailscale-svc-lb
TAG=latest

build: build-controller build-runtime

push: push-controller push-runtime

build-controller:
	docker build . -t $(REPOSITORY)-controller:$(TAG)

push-controller: build-controller
	docker push $(REPOSITORY)-controller:$(TAG)

build-runtime:
	cd runtime && docker build . -t $(REPOSITORY):$(TAG)

push-runtime: build-runtime
	docker push $(REPOSITORY):$(TAG)
