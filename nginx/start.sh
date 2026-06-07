#!/bin/sh
set -e

# Lê o nameserver do /etc/resolv.conf (DNS interno do Railway)
RESOLVER=$(grep nameserver /etc/resolv.conf | awk '{print $2}' | head -1)
echo "Using DNS resolver: $RESOLVER"

# Substitui o placeholder no nginx.conf
sed -i "s/NGINX_RESOLVER/$RESOLVER/g" /etc/nginx/nginx.conf

# Inicia o nginx
exec nginx -g 'daemon off;'
