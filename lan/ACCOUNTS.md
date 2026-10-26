# Arena accounts, website and database

In the extracted `server/` directory, copy `.env.example` to `.env`. Fill in
`ARENA_ADMIN_TOKEN`, `ARENA_DB_PASSWORD` and `ARENA_DB_EDITOR_PASSWORD` yourself.
Each secret must be longer than 1 character; there are no character restrictions.
The example also exposes the host ports and bind addresses for editing.

Start directly with Compose:

```sh
docker compose up -d --build
```

`docker-compose up -d --build` also works with the standalone Compose command.
Docker and Compose are the only host dependencies. No start script or secret
generator is needed. Compose refuses missing/empty secrets before starting.
Allow time for MariaDB initialization on the first start.

Open `http://SERVER:8080/`. First registration requires the `ARENA_ADMIN_TOKEN`
from `.env` and creates the sole initial administrator. Later registrations use
only username and password. No email or verification service is involved.
Passwords must be longer than 1 character and are stored with salted scrypt hashes.
Usernames are case-insensitive ASCII letters/numbers/underscore, 3–32 characters.
Display names are separate and can be changed on My fighter. Built-in avatars
and card backgrounds are selectable there. Custom asset uploads are not enabled.

The administrator's Server tab displays the last 200 lines (maximum 64 KiB) of
the game-server log and can restart the game worker after confirmation. This
disconnects active games. It does not restart MariaDB or erase accounts. The
web service has no Docker socket and cannot run arbitrary admin commands.

## Ports and secrets

The container publishes game TCP/UDP 27150, HTTP 8080 and MariaDB TCP 3306. Compose
variables `SZERO_PORT`, `ARENA_WEB_PORT` and `ARENA_DB_PORT` change host ports.
`SZERO_BIND_IP` defaults to 0.0.0.0; `ARENA_DB_BIND_IP` separately defaults to
0.0.0.0 to permit an external database editor, as requested. Set it to 127.0.0.1
when using an SSH tunnel instead.

For a database editor, use host SERVER, port 3306, database `arena`, user
`arena_editor` and password `ARENA_DB_EDITOR_PASSWORD` from `.env`. This account
can edit the Arena schema, not global server administration. The application
uses separate user `arena` and `ARENA_DB_PASSWORD`; root is local Unix-socket-only.
Changing these `.env` passwords then recreating the container updates database
credentials without deleting the data. Do not expose the database to untrusted
networks. Back up the database before manual edits, particularly account IDs and
result-event records. Never share `.env` or put it in a public archive.

The server never creates or rewrites `.env`. Keep your existing `.env` when
updating the package. No host Python installation is needed.

## Reverse proxy

The API and assets use relative paths, and no public absolute backend URLs are
returned. A proxy can serve the site at its root or a subpath ending in `/`.
Strip the prefix before forwarding. Preserve `Host`. Use HTTPS when credentials
cross an untrusted network. Set `ARENA_PUBLIC_URL=https://arena.example/` (or the
full public subpath) in `.env` when the proxy rewrites Host; this controls the
same-origin write check. Forwarded-for headers are not trusted for authentication
rate limits. For a proxy, all forwarded users consequently share its source-IP
limit of 12 login/registration attempts per minute.

Example nginx root proxy:

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $http_host;
}
```

Example subpath:

```nginx
location = /arena { return 308 /arena/; }
location /arena/ {
    proxy_pass http://127.0.0.1:8080/;
    proxy_set_header Host $http_host;
}
```

The launcher uses only the configured game host and port (default27150) for
login and remembered-session checks. It does not ask for the website URL and
does not use the HTTP proxy. The website can still be reverse proxied for
registration and profile management. An HTTP reverse proxy does not carry the
game TCP/UDP service.

## Launcher login

The PLAYER area has Quick play and Login tabs. Quick play uses the entered
player name and cannot enter Ranked. Login has username/password fields and an
explicit Login button. Clicking Login verifies the credentials through the game
server and immediately saves the remembered session. Your account display name
becomes the game's player name.

The password itself is not saved. A protected reusable login token remembers
the login, so subsequent launches need no password entry. It is scoped to the
game host, port and username. A password hash cannot be replayed for login; the
token provides that functionality and can be revoked server-side by removing
its `account_sessions` record. Website sign-out revokes only the browser's session.
Editing the server address, username or password requires clicking Login again.
Launch revalidates the remembered token before starting anything. Other launcher
settings still save only on Launch Game, including the optional INI name update.

The TCP protocol has one bounded JSON line per temporary connection:
`op:account, version:2, action:login` with username/password, or `action:me` with
token. It returns an account event with a verified profile/token or a generic
refusal. These sockets never become lobby peers or allocate UDP sessions.
Credentials and tokens are not written to game-server logs.

## Persistence and rankings

The named `server-data` volume stores MariaDB data, accounts, login sessions,
profiles, per-mode rankings and result events. `server-logs` stores game logs.
Restarting the game worker or container preserves them. `docker compose down`
preserves named volumes; `docker compose down -v` deletes them. Keep the same
Compose project name/directory to reuse the same volumes.

Tables are `accounts`, `account_sessions`, `rankings`, `rank_events` and
`arena_setup`. A profile has validated built-in `avatar`/`banner` IDs and a
`profile_json` extension object. Rankings use independent `single`, `dp`, `team`
rows with rating, wins, losses, draws, games and updated timestamp. Session
tokens expire in 30 days, are stored hashed, and can be revoked by sign-out.
The launcher never stores passwords. Browser sessions are per-tab sessionStorage.

The server-only `AccountStore.record_result` is transactional and idempotent by
match ID. LAN Elo starts at 1000 and uses K=32. It applies one result to both
participants and rejects conflicting duplicates. This is a new LAN rating
system, not the official game's ranking formula or official progression.

Automatic native Ranked result ingestion now requires complementary typed
reports from both authenticated participants of the server-issued match. Each
own report is durable before its ACK; consensus commits once. Native completion
outcome is not used as a score. Missing/conflicting/unknown results and self-play
remain unrated. The new ranked_reports table and win_streak/max_win_streak
columns migrate automatically. Website counters and native Single/DP lifetime
win-rate views reload confirmed statistics. Official native rank titles remain
separate from LAN Elo. See DEPLOYMENT.md for expanding matchmaking settings and
the remaining result-menu exit error.

## Implementation and checks

The website is Python, with no PHP or PHP shell bridge. The image installs the
Debian MariaDB server package and pinned PyMySQL 1.1.2. MariaDB, website and game
worker run under the same nonroot UID 10001. The supervisor coordinates shutdown
and a fixed game-restart sentinel. The filesystem is read-only except named
data/log volumes and temporary memory. No game files enter the server image.

MariaDB initialization uses the documented socket-root setup and skips the test
database: [mariadb-install-db](https://mariadb.com/docs/server/clients-and-utilities/deployment-tools/mariadb-install-db).
SQLite is available only as an explicit local development/test backend through
`ARENA_SQLITE_PATH`, never as a silent production fallback.
