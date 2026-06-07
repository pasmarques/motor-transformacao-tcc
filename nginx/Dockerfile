FROM nginx:alpine
COPY nginx.conf /etc/nginx/nginx.conf
COPY start.sh /start.sh
RUN sed -i 's/\r$//' /start.sh && chmod +x /start.sh
CMD ["/start.sh"]
