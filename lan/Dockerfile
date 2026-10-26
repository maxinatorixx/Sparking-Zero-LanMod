FROM python:3.12-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
# MariaDB and all application services share one container. No Docker socket.
RUN apt-get update && apt-get install -y --no-install-recommends mariadb-server \
    && rm -rf /var/lib/apt/lists/* /var/lib/mysql/* \
    && pip install --no-cache-dir PyMySQL==1.1.2
COPY szero_lan.py native_sessions.py native_session_transactions.py native_search.py \
     native_identity_diagnostics.py native_session_codec.py lan_identity.py installer.py backend_services.py \
     account_store.py arena_web.py arena_supervisor.py native_rank.py native_profile.py elo_matchmaking.py ./
COPY web ./web
COPY server.example.json ./server.json
RUN groupadd --gid 10001 szero && useradd --uid 10001 --gid 10001 --no-create-home szero \
    && mkdir /logs /data && chown 10001:10001 /logs /data
USER 10001:10001
EXPOSE 27150/tcp 27150/udp 8080/tcp 3306/tcp
VOLUME ["/logs", "/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD python -c "import json,socket,urllib.request; c=json.load(open('/app/server.json')); s=socket.create_connection(('127.0.0.1',c['server_port']),2); s.close(); urllib.request.urlopen('http://127.0.0.1:8080/api/status',timeout=2).read()"
CMD ["python", "arena_supervisor.py"]
