#!/bin/bash
# Gera certificado SSL autoassinado para desenvolvimento local.
# Em producao, substitua pelos arquivos do Let's Encrypt.

mkdir -p nginx/ssl

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem \
  -subj "/C=BR/ST=SP/L=SaoPaulo/O=TCC/CN=localhost"

echo "Certificado gerado em nginx/ssl/"
