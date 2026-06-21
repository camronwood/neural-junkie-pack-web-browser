.PHONY: verify pack-zip clean

verify:
	./scripts/verify-pack.sh

pack-zip:
	./scripts/build-pack-zip.sh

clean:
	rm -rf dist
