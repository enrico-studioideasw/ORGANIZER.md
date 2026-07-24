# Local encrypted keyring

This clean kit installs a local AES-256-GCM keyring.

It contains only the program. It does not contain the source machine's vault,
encryption key or credentials.

## Installation

```sh
install -d -m 700 /root/.codex-keyring
install -m 700 keyring.php /root/.codex-keyring/keyring.php
/root/.codex-keyring/keyring.php init
```

`init` generates a new random key and an empty vault locally. Both files are
created with mode `600`.

## Usage

```sh
printf '%s' 'secret-value' |
  /root/.codex-keyring/keyring.php set logical-name

/root/.codex-keyring/keyring.php list
/root/.codex-keyring/keyring.php get logical-name
/root/.codex-keyring/keyring.php delete logical-name
```

Never print the result of `get` in chats, logs or project diaries. Maintained
memory may contain the logical entry name and its usage procedure, but never
the secret.

Each machine should have its own key and vault. Do not copy `keyring.key` or
`keyring.vault` from another system unless an explicitly authorized and
protected migration is being performed.
