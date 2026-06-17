# HTTPS Deployment With CIT/ITO Server Certificate

Use this on a CIT/LRZ VM when the study should be reachable through HTTPS, for example:

```text
https://iivm7.cit.tum.de/HAIC_study/
```

The repository contains the Docker and nginx configuration. The certificate, CSR, and private key must be created and stored only on the VM. Never commit files from `certs/`.

The CIT/ITO certificate request page was not reachable from this environment, so this document follows the same CSR-based server certificate flow already used for the other VM.

## 1. DNS And Firewall

Before requesting the certificate, make sure the VM has a fully qualified domain name, for example:

```text
iivm7.cit.tum.de
```

Ask LRZ/IT to keep these inbound ports open for the VM:

```text
TCP 80
TCP 443
```

Port 80 is used for the HTTP-to-HTTPS redirect. Port 443 serves the study over HTTPS.

## 2. Create Private Key And CSR On The VM

Run this on the VM from the repository directory:

```bash
chmod +x scripts/create-cit-csr.sh
./scripts/create-cit-csr.sh iivm7.cit.tum.de
```

Example:

```bash
./scripts/create-cit-csr.sh iivm7.cit.tum.de
```

This creates:

```text
certs/iivm7.cit.tum.de.key
certs/iivm7.cit.tum.de.csr
certs/server.key -> iivm7.cit.tum.de.key
```

Submit `certs/iivm7.cit.tum.de.csr` through the CIT/ITO server certificate process.

If the VM needs additional DNS names in the same certificate, pass them after the primary hostname:

```bash
./scripts/create-cit-csr.sh iivm7.cit.tum.de alias.cit.tum.de
```

## 3. Install Returned Certificate

After CIT/ITO returns the server certificate and intermediate chain, copy the files to `certs/` on the VM.

The HTTPS nginx config expects:

```text
certs/server.key
certs/server.fullchain.pem
```

If CIT/ITO gives separate files, create the full chain by concatenating the server certificate first, then the intermediate certificates:

```bash
cat certs/iivm7.cit.tum.de.crt certs/intermediate-ca.pem > certs/server.fullchain.pem
chmod 600 certs/server.key
chmod 644 certs/server.fullchain.pem
```

Adjust the received file names as needed.

## 4. Configure The VM Environment

In the VM-local `.env.docker`, use:

```env
STUDY_HTTP_PORT=80
STUDY_HTTPS_PORT=443
STUDY_PUBLIC_URL=https://iivm7.cit.tum.de
```

Example:

```env
STUDY_HTTP_PORT=80
STUDY_HTTPS_PORT=443
STUDY_PUBLIC_URL=https://iivm7.cit.tum.de
```

Keep real secrets, such as `OPENROUTER_API_KEY`, only in `.env.docker` on the VM.

## 5. Start HTTPS Deployment

Use the HTTPS compose override:

```bash
sudo docker compose -f docker-compose.yml -f docker-compose.https.yml up --build -d
```

If the VM only has legacy Docker Compose:

```bash
sudo docker-compose -f docker-compose.yml -f docker-compose.https.yml up --build -d
```

## 6. Test

```bash
curl -I http://iivm7.cit.tum.de/HAIC_study/
curl -I https://iivm7.cit.tum.de/HAIC_study/
curl -I https://iivm7.cit.tum.de/api/health
```

Expected:

```text
HTTP on port 80 -> 301 redirect to HTTPS
HTTPS on port 443 -> 200 OK
```

Participant URL:

```text
https://iivm7.cit.tum.de/HAIC_study/?Lab_participant_ID=LAB_001
```

## 7. Renew Or Replace Certificate

When renewing the certificate, keep the existing private key unless CIT/ITO requires a new one. If you receive a new server certificate and chain, replace only:

```text
certs/server.fullchain.pem
```

Then reload the deployment:

```bash
sudo docker compose -f docker-compose.yml -f docker-compose.https.yml restart study
```
