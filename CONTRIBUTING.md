# Contributing

Small corrections can be made directly in the GitHub editor. For a new article, create a branch and run:

```bash
make new SLUG=short-descriptive-slug
make dev
```

Before opening a pull request:

- keep the post as a draft until it is ready, but remember its source is public after you push it;
- put screenshots in `static/images/<year>/<month>/` and use `/images/...` URLs;
- add a useful excerpt and two to four topics;
- run `make check`;
- remove private hostnames, tokens, addresses, and customer data from examples.

The article slug becomes its permanent URL, so avoid changing it after publication.
