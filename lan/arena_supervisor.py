"""One-container process supervisor: nonroot MariaDB, website, game server.

The admin website can only request restart of the game child via a fixed file.
It never receives Docker privileges or an arbitrary command execution endpoint.
"""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

DATA = Path(os.getenv("ARENA_DATA_DIR", "/data"))
SOCKET = str(DATA / "run/mysql.sock")


def stop(process):
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)


def read_secrets(environment):
    secrets = {}
    for key in ("ARENA_ADMIN_TOKEN", "ARENA_DB_PASSWORD", "ARENA_DB_EDITOR_PASSWORD"):
        value = environment.get(key, "")
        if not isinstance(value, str) or len(value) <= 1:
            raise ValueError("Missing/invalid " + key + ". Set a value longer than 1 character in .env.")
        secrets[key] = value
    return secrets


def main():
    secrets = read_secrets(os.environ)
    import pymysql
    for folder in (DATA / "mysql", DATA / "run", DATA / "mysql-tmp", DATA / "mysql-files"):
        folder.mkdir(parents=True, exist_ok=True)
    if not (DATA / "mysql/mysql").exists():
        subprocess.run(["mariadb-install-db", "--no-defaults", "--datadir=" + str(DATA / "mysql"),
                        "--auth-root-authentication-method=socket", "--auth-root-socket-user=szero",
                        "--skip-test-db", "--skip-name-resolve"], check=True,
                       stdout=subprocess.DEVNULL)
    database = web = game = None
    closing = False

    def shutdown(signum, frame):
        nonlocal closing
        closing = True

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    restart = DATA / "run/restart-game"
    restart.unlink(missing_ok=True)
    try:
        database = subprocess.Popen(["mariadbd", "--no-defaults", "--datadir=" + str(DATA / "mysql"),
            "--socket=" + SOCKET, "--pid-file=" + str(DATA / "run/mysql.pid"),
            "--bind-address=0.0.0.0", "--port=3306", "--skip-name-resolve",
            "--tmpdir=" + str(DATA / "mysql-tmp"), "--innodb-buffer-pool-size=64M",
            "--innodb-log-file-size=32M", "--max-connections=64", "--local-infile=0",
            "--secure-file-priv=" + str(DATA / "mysql-files"), "--character-set-server=utf8mb4", "--collation-server=utf8mb4_bin"])
        deadline = time.monotonic() + 60
        while not closing:
            try:
                connection = pymysql.connect(unix_socket=SOCKET, user="szero", connect_timeout=2, autocommit=True)
                break
            except pymysql.MySQLError:
                if database.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("MariaDB failed to become ready")
                time.sleep(.1)
        else:
            return
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("CREATE DATABASE IF NOT EXISTS arena CHARACTER SET utf8mb4 COLLATE utf8mb4_bin")
                # No SQL interpolation of passwords. Both application and editor
                # are restricted to the Arena schema; root stays Unix-socket-only.
                for username, host, password in (("arena", "127.0.0.1", secrets["ARENA_DB_PASSWORD"]),
                                                  ("arena_editor", "%", secrets["ARENA_DB_EDITOR_PASSWORD"])):
                    cursor.execute("CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s", (username, host, password))
                    cursor.execute("ALTER USER %s@%s IDENTIFIED BY %s", (username, host, password))
                    cursor.execute("GRANT ALL PRIVILEGES ON arena.* TO %s@%s", (username, host))
        environment = dict(os.environ, ARENA_DB_HOST="127.0.0.1", ARENA_DB_PORT="3306", ARENA_DB_USER="arena", ARENA_DB_NAME="arena")
        web = subprocess.Popen([sys.executable, "arena_web.py"], env=environment)

        def start_game():
            return subprocess.Popen([sys.executable, "szero_lan.py", "server", "--config", "/app/server.json", "--log", "/logs/server.log"], env=environment)

        game = start_game()
        print("Arena ready: website :8080, game TCP/UDP :27150, MariaDB :3306", flush=True)
        while not closing:
            if database.poll() is not None or web.poll() is not None:
                raise RuntimeError("Required Arena service exited; stopping container")
            if restart.exists():
                restart.unlink(missing_ok=True)
                print("Administrator requested game server restart", flush=True)
                stop(game)
                game = start_game()
            elif game.poll() is not None:
                raise RuntimeError("Game server exited; stopping container")
            time.sleep(.2)
    finally:
        for process in (game, web, database):
            stop(process)


if __name__ == "__main__":
    main()
