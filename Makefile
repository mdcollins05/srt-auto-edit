.PHONY: help build test generate-expected show-rules dry-run-all dry-run-trace dry-run-clean dry-run-ads dry-run-malformed

CONFIG = -c /config/settings.yaml

help:
	@echo "Available targets:"
	@echo "  build               Build the Docker image"
	@echo "  test                Compare subtitle output and console output against baselines"
	@echo "  generate-expected   Regenerate both baselines (subtitle files and console logs)"
	@echo "  show-rules          List all rules loaded from the test config"
	@echo "  dry-run-all         Verbose dry-run on all test input files"
	@echo "  dry-run-trace       Full -vvv rule trace on all test input files"
	@echo "  dry-run-clean       Verbose dry-run on clean.srt"
	@echo "  dry-run-ads         Verbose dry-run on ads-and-credits.srt"
	@echo "  dry-run-malformed   Verbose dry-run on malformed.srt"
	@echo ""
	@echo "Typical first-run workflow:"
	@echo "  make build && make generate-expected && make test"

build:
	docker compose build

test:
	docker compose run --rm test

generate-expected:
	docker compose run --rm generate-expected

show-rules:
	docker compose run --rm srt-auto-edit -r $(CONFIG)

dry-run-all:
	docker compose run --rm srt-auto-edit -v $(CONFIG) /test-data/

dry-run-trace:
	docker compose run --rm srt-auto-edit -vvv $(CONFIG) /test-data/

dry-run-clean:
	docker compose run --rm srt-auto-edit -v $(CONFIG) /test-data/clean.srt

dry-run-ads:
	docker compose run --rm srt-auto-edit -v $(CONFIG) /test-data/ads-and-credits.srt

dry-run-malformed:
	docker compose run --rm srt-auto-edit -v $(CONFIG) /test-data/malformed.srt
