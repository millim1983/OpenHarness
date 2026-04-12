# Git Private Development Strategy

## Current Remote Roles

- `upstream`: original public project, `HKUDS/OpenHarness`.
- `origin`: personal fork, `millim1983/OpenHarness`.
- `private`: private development repository to add for unpublished work.

## Privacy Rule

Do not push active private development work to `origin` while the fork is public.

`upstream` is only for fetching original project updates. It does not receive local work unless explicitly pushed, and direct pushes to `upstream` normally require maintainer permission.

Push private development branches only to the private remote:

```bash
git push -u private <branch-name>
```

## Recommended Flow

1. Keep `upstream` connected to the original project.
2. Keep `origin` connected to the public fork, but do not push private work there.
3. Create a separate private GitHub repository.
4. Add it as `private`.
5. Commit local Ubuntu development work on a feature branch.
6. Push that branch to `private`.
7. Only push to `origin` or open an upstream pull request when the work is intentionally public.

## Example Commands

```bash
git remote add private https://github.com/millim1983/OpenHarness-private-dev.git
git switch -c web-mvp-rag
git push -u private web-mvp-rag
```

## Server Development Note

The Ubuntu workspace is the current source of truth for Web MVP and RAG development. Do not continue private development in the old Windows `E:` drive clone unless it has been resynced from the private repository.
