External access must be set up via another add-on's reverse proxy, preferrably with SSL.
I'd recommend `NGINX Home Assistant SSL proxy <https://github.com/home-assistant/addons/tree/master/nginx_proxy>`_ as it works quite well for me with this with this config:

/share/nginx_proxy/matrix.conf::

    server {
        server_name matrix.example.net;

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
            proxy_pass http://674b3982-mijofa-matrixdotorg-synapse:8008;
            proxy_set_header X-Forwarded-For $remote_addr;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Host $host;
    
            # Nginx by default only allows file uploads up to 1M in size
            # Increase client_max_body_size to match max_upload_size defined in homeserver.yaml
            client_max_body_size 50M;
        }
    }
