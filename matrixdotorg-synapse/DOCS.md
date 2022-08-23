External access must be set up via another add-on's reverse proxy, preferrably with SSL.
I'd recommend [NGINX Home Assistant SSL proxy](https://github.com/home-assistant/addons/tree/master/nginx_proxy) as it works quite well for me with this config:

/share/nginx\_proxy/matrix.conf:

    server {
        server_name matrix.example.net;

        # Variable and resolver needed here so that Nginx doesn't refuse to start when it can't resolve this DNS name
        resolver dns.local.hass.io valid=30s;
        set $matrix_backend 674b3982-matrixdotorg-synapse:8008;

        listen 443 ssl http2;
        listen [::]:443 ssl http2;

        # For the federation port
        listen 8448 ssl http2 default_server;
        listen [::]:8448 ssl http2 default_server;

        ssl_session_timeout 1d;
        ssl_session_cache shared:MozSSL:10m;
        ssl_session_tickets off;
        ssl_certificate /ssl/fullchain.pem;
        ssl_certificate_key /ssl/privkey.pem;

        # dhparams file
        ssl_dhparam /data/dhparams.pem;

        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        proxy_buffering off;

        location ~ ^(/_matrix|/_synapse/client) {
            # note: do not add a path (even a single /) after the port in `proxy_pass`,
            # otherwise nginx will canonicalise the URI and cause signature verification
            # errors.
            proxy_pass http://$matrix_backend;
            proxy_set_header X-Forwarded-For $remote_addr;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Host $host;

            # Nginx by default only allows file uploads up to 1M in size
            # Increase client_max_body_size to match max_upload_size defined in homeserver.yaml
            client_max_body_size 50M;
        }
    }

Postgres support requires a role & database be created in the SQL server first.
I use the [TimescaleDB](https://github.com/Expaso/hassos-addon-timescaledb) addon with this config,
but you could just as easily use an external PostgreSQL server:

    # Requires manually creating the DB & user with something like this:
    # $ psql --user postgres -c "DO $$ begin IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'synapse') THEN RAISE NOTICE 'Synapse role already exists. Skipping.'; ELSE CREATE ROLE synapse WITH PASSWORD 'CorrectBatteryHorseStaple LOGIN CREATEDB'; END IF; end $$"
    # $ psql --user postgres -c "CREATE DATABASE synapse LOCALE = 'C' ENCODING = 'UTF8' TEMPLATE = 'template0' OWNER = 'synapse'"
    database:
      name: "psycopg2"
      args:
        user: "synapse"
        password: "{postgres_password}"
        # password: "CorrectBatteryHorseStaple"
        database: "synapse"
        host: "77b2833f-timescaledb"
        port: 5432
        cp_min: 5
        cp_max: 10
