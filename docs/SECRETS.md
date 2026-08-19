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

3. Unlock:
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
