# The Secretary Documentation website

This repository owns the HTML template, CSS, renderer, and deployment. It does NOT own or store documentation Markdown or generated command data.

Canonical content lives exclusively in Gshergd/The-Secretary:
- Documentation/**/*.md (guides, command manuals, changelogs)
- secretary-commands.js (command reference data)

## Automatic update flow

1. Change content in The Secretary repo and push to main.
2. Its notify-documentation.yml workflow sends a repository_dispatch event to this repo.
3. This repo checks out the latest main from The Secretary into an ignored temporary .source/ directory.
4. The static builder reads those files directly and deploys the resulting HTML/CSS through GitHub Pages.

No Markdown is copied into this repository's Git history. There is no manual syncing. Website code changes here also trigger a rebuild against the current source content.

## One-time cross-repository authentication

The normal GITHUB_TOKEN is scoped to its own repository, so a dispatch to another repository requires a credential:

- In **The Secretary** repository, add Actions secret **DOCS_REPO_TOKEN**: a fine-grained personal access token scoped only to thesecretary-docs.github.io, with **Contents: read and write** (required by GitHub's repository-dispatch API).
- If **The Secretary is private**, add Actions secret **SECRETARY_SOURCE_TOKEN** in this website repo: a fine-grained token scoped only to The Secretary, with **Contents: read**. Public source repositories need no source token.
- Enable GitHub Pages using GitHub Actions in this repo. The pages workflow must exist on its default main branch to receive repository_dispatch events.

The public output includes the documentation you maintain in The Secretary even if that source repo is private. Bot secrets, database files and application code are not uploaded.

## Local build

Python 3.10+, no third-party packages:

```sh
python scripts/build.py --source-root ../Gshergd/The-Secretary
```

The source path can point to any existing The Secretary checkout. The renderer reads it without modifying it. Generated website output is dist/ and is ignored by Git.

For local preview:

```sh
python scripts/build.py --source-root ../Gshergd/The-Secretary --base-path ""
python -m http.server 8080 --directory dist
```

Website template and embedded CSS are maintained in scripts/rendering.py; the builder exports the CSS to dist/styles.css. Source content is never read from a local Documentation folder in this website repo.

Expected published URL: https://gshergd.github.io/thesecretary-docs.github.io/

Changelogs retain all source files, ten per page. Named versions sort by version; unversioned notes sort by filename. Commit dates are not invented.
