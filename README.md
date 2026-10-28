# BadgerOps

The source for the BadgerOps technical field notes at `blog.badgerops.net`. The site is built with Hugo and deployed to GitHub Pages on every push to `main`.

## Write a post

You need [Hugo](https://gohugo.io/installation/) 0.169.0 or newer.

```bash
make new SLUG=my-useful-post
make dev
```

Edit the generated file in `content/posts/`, then open `http://localhost:1313`. Drafts are visible locally and excluded from production. Their source is still visible in this public repository, so do not commit private material. Set `draft: false` when the post is ready.

Posts are regular Markdown. Add topics in front matter:

```yaml
topics:
  - Kubernetes
  - Homelab
```

No Node install, theme submodule, CMS, or build database is required.

## Common commands

```bash
make dev       # local server with drafts and future posts
make build     # production build
make check     # production build plus generated-site checks
```

The GitHub Actions workflow builds pull requests without deploying them. Merges to `main` deploy automatically.

## Ghost migration

The one-time importer is kept in `scripts/import_ghost.py` for provenance and future re-runs:

```bash
python3 scripts/import_ghost.py /path/to/export.json --download-assets
```

The export itself is intentionally not committed because it contains account and site metadata. Drafts are skipped by default; use `--include-drafts` only in a repository where their source may safely be visible.
