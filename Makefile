.PHONY: build-api-base build-api

API_IMAGE_TAG ?= latest

# Load environment variables
include docker/.env

# Export variables to shell commands
export REGISTRY_URL
export API_IMAGE_TAG

build-api-base: ## Build and push base image with all dependencies
	docker build \
		-f docker/base-images/base-api.Dockerfile \
		-t $(REGISTRY_URL)/api-base:$(API_IMAGE_TAG) \
		api/
	docker push $(REGISTRY_URL)/api-base:$(API_IMAGE_TAG)

build-api: ## Build and push API application image
	cd docker && docker compose -f docker-compose.build.yml build api
	docker push $(REGISTRY_URL)/api:$(API_IMAGE_TAG)
