#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <fully-qualified-domain-name> [additional-dns-name ...]" >&2
  echo "Example: $0 iivm7.cit.tum.de" >&2
  exit 1
fi

FQDN="$1"
shift

mkdir -p certs
chmod 700 certs

SAN="DNS:${FQDN}"
for DNS_NAME in "$@"; do
  SAN="${SAN},DNS:${DNS_NAME}"
done

openssl req -new -newkey rsa:3072 -nodes \
  -keyout "certs/${FQDN}.key" \
  -out "certs/${FQDN}.csr" \
  -subj "/CN=${FQDN}" \
  -addext "subjectAltName=${SAN}"

chmod 600 "certs/${FQDN}.key"

ln -sf "${FQDN}.key" certs/server.key

echo
echo "Created:"
echo "  certs/${FQDN}.key"
echo "  certs/${FQDN}.csr"
echo
echo "Submit certs/${FQDN}.csr to the CIT/ITO server certificate process."
echo "After receiving the certificate, create certs/server.fullchain.pem as documented in HTTPS_CIT_CERTIFICATE.md."
