.PHONY: verify pack-zip pack-smoke setup-playwright clean

verify:
	./scripts/verify-pack.sh

pack-zip:
	./scripts/build-pack-zip.sh

setup-playwright:
	./scripts/setup-playwright.sh

pack-smoke:
	./scripts/pack-smoke.sh

clean:
	rm -rf dist
