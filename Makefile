.PHONY: dev build check new

HUGO ?= hugo

dev:
	$(HUGO) server --buildDrafts --buildFuture --disableFastRender

build:
	$(HUGO) --gc --minify --cleanDestinationDir

check: build
	python3 scripts/check_build.py public

new:
	@test -n "$(SLUG)" || (echo "Usage: make new SLUG=my-post-slug" && exit 1)
	$(HUGO) new content posts/$(SLUG).md
