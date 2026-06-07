FROM nginx:alpine
COPY nginx.conf /etc/nginx/nginx.conf.template
CMD ["sh", "-c", "export RESOLVER=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}' | head -1) && envsubst '${RESOLVER}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf && nginx -g 'daemon off;'"]
