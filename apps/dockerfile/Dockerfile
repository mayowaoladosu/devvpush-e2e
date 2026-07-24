FROM busybox:1.37.0

WORKDIR /www
COPY index.html /www/index.html

USER 65534:65534
EXPOSE 8000

CMD ["busybox", "httpd", "-f", "-p", "8000", "-h", "/www"]
