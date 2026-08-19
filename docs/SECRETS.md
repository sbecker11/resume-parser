# Secrets: `.env` via git-crypt

`.env` is tracked in this repo but encrypted at rest with
[git-crypt](https://github.com/AGWA/git-crypt). GitHub only ever sees the
encrypted blob (starts with `\0GITCRYPT`) — never the plaintext values.
Anyone who clones the repo *without* the key gets the encrypted file and
nothing else; nothing is exposed by the repo being public.

This is a separate, unrelated mechanism from **GitHub Actions secrets**
(`Settings → Secrets and variables → Actions`, used by `.github/workflows/*`).
Those secrets power CI/CD runs on GitHub's runners and can never be read back
out (by design — they're write-only). git-crypt is what makes `.env` itself
travel with `git clone`/`git pull` for local development.

## When and how to decrypt .env

**When you need to run `git-crypt unlock`:**

- **First clone on a new machine.** `.env` in a fresh `git clone` is still
  the encrypted blob — the repo hasn't been unlocked there yet.
- **After restoring or rotating the key** (e.g. new laptop, key was
  regenerated per "Rotating the key" below).
- **Any time `.env` in your working tree is still ciphertext.** Signs of
  this: `python-dotenv`/`load_dotenv_safely()` logs a warning like "likely
  still git-crypt encrypted" (see `src/resume_parser/env_loader.py`) instead
  of loading real values, or opening `.env` in an editor shows
  binary/garbage instead of `KEY=value` lines.

**How to unlock:**

```bash
git-crypt unlock ~/.git-crypt-keys/resume-parser.key
```

**How to tell it worked:**

```bash
git-crypt status
```
Should list `.env` as `not encrypted` (i.e. decrypted in the working tree —
the label refers to the working-tree state, not the git-history blob, which
always stays encrypted). You can also just open `.env` directly: plaintext
`KEY=value` lines means it worked; a line starting with `\0GITCRYPT` means
it's still locked.

You only need to run `unlock` once per clone/checkout of the repo on a given
machine — it stays decrypted across `git pull`/`git checkout` after that, for
as long as the key file is present at the path you unlocked with.

CI never unlocks — see `docs/TEST-COVERAGE.md` for why tests don't need a
real `.env`.

## First time on a new machine

1. Clone the repo as normal:
   ```bash
   git clone git@github.com:sbecker11/resume-parser.git
   cd resume-parser
   ```
   At this point `.env` exists in the working tree but is still the
   encrypted blob — trying to load it will fail (e.g. `python-dotenv` will
   read garbage).

2. Get the key `resume-parser.key` (see "Where the key lives" below) onto
   the new machine, e.g.:
   ```bash
   scp me@old-machine:~/.git-crypt-keys/resume-parser.key ~/.git-crypt-keys/
   ```

3. Unlock (see "When and how to decrypt .env" above):
   ```bash
   git-crypt unlock ~/.git-crypt-keys/resume-parser.key
   ```
   `.env` is now decrypted in your working tree. Future `git pull`s stay
   decrypted automatically as long as the repo is unlocked.

## Where the key lives

`~/.git-crypt-keys/resume-parser.key` (mode `600`, outside any git repo).
**Back this up somewhere durable and out-of-band** (password manager, an
encrypted volume, a second machine) — it is the *only* way to decrypt `.env`
from git history. If it's lost, the encrypted commits become permanently
unrecoverable (you'd `git-crypt init` fresh and lose the encrypted history,
though the current plaintext `.env` on disk would still be fine).

## Rotating the key (if it ever leaks)

`git-crypt` has no built-in rotation. If the key is ever exposed:
1. Generate a fresh secret value for anything in `.env` that's actually
   sensitive (API keys, etc.) at the provider.
2. `git-crypt init` a fresh key (or `rm -rf` + re-init), re-encrypt `.env`
   with the new values, and force-push if you want old encrypted blobs gone
   from history too (optional — they're only a threat if the *old* key also
   leaks).

## Adding more secret files later

Add a line to `.gitattributes`:
```
path/to/file filter=git-crypt diff=git-crypt
```
then `git add` the file normally — the filter encrypts it transparently.
