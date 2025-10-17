#!/bin/bash
# mTLS Certificate Generator for MCPeeker
# Reference: FR-010 (mTLS enforcement), research.md (90-day rotation)
#
# Generates:
# - Root CA certificate
# - Service certificates for all MCPeeker services
# - Client certificates for inter-service communication
#
# Usage: ./generate-certs.sh [output_dir]

set -e

OUTPUT_DIR="${1:-./certs}"
CERT_VALIDITY_DAYS=90  # FR-010: 90-day rotation policy

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}MCPeeker mTLS Certificate Generator${NC}"
echo -e "${YELLOW}Validity: ${CERT_VALIDITY_DAYS} days${NC}"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

# Generate Root CA
echo -e "${GREEN}[1/7] Generating Root CA...${NC}"
openssl genrsa -out ca.key 4096
openssl req -new -x509 -days "$CERT_VALIDITY_DAYS" -key ca.key -out ca.crt \
  -subj "/C=US/ST=California/L=San Francisco/O=MCPeeker/OU=Security/CN=MCPeeker Root CA"

echo -e "${GREEN}✓ Root CA created: ca.crt, ca.key${NC}"

# Function to generate service certificate
generate_service_cert() {
  local service_name=$1
  local dns_names=$2

  echo -e "${GREEN}[2/7] Generating certificate for ${service_name}...${NC}"

  # Generate private key
  openssl genrsa -out "${service_name}.key" 2048

  # Create config file for Subject Alternative Names (SAN)
  cat > "${service_name}.cnf" <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C=US
ST=California
L=San Francisco
O=MCPeeker
OU=${service_name}
CN=${service_name}.mcpeeker.local

[v3_req]
keyUsage = keyEncipherment, dataEncipherment, digitalSignature
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = @alt_names

[alt_names]
${dns_names}
EOF

  # Generate CSR
  openssl req -new -key "${service_name}.key" -out "${service_name}.csr" \
    -config "${service_name}.cnf"

  # Sign with CA
  openssl x509 -req -in "${service_name}.csr" -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out "${service_name}.crt" -days "$CERT_VALIDITY_DAYS" \
    -extensions v3_req -extfile "${service_name}.cnf"

  # Cleanup
  rm "${service_name}.csr" "${service_name}.cnf"

  echo -e "${GREEN}✓ Certificate created: ${service_name}.crt, ${service_name}.key${NC}"
}

# Generate service certificates
generate_service_cert "scanner" "DNS.1=scanner,DNS.2=scanner.mcpeeker.local,DNS.3=localhost"
generate_service_cert "correlator" "DNS.1=correlator,DNS.2=correlator.mcpeeker.local,DNS.3=localhost"
generate_service_cert "judge" "DNS.1=judge,DNS.2=judge.mcpeeker.local,DNS.3=localhost"
generate_service_cert "registry-api" "DNS.1=registry-api,DNS.2=registry-api.mcpeeker.local,DNS.3=localhost,DNS.4=api.mcpeeker.local"
generate_service_cert "signature-engine" "DNS.1=signature-engine,DNS.2=signature-engine.mcpeeker.local,DNS.3=localhost"
generate_service_cert "frontend" "DNS.1=frontend,DNS.2=frontend.mcpeeker.local,DNS.3=localhost,DNS.4=mcpeeker.local"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Certificate Generation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Output directory: ${YELLOW}$(pwd)${NC}"
echo ""
echo "Generated certificates:"
echo "  - ca.crt, ca.key (Root CA)"
echo "  - scanner.crt, scanner.key"
echo "  - correlator.crt, correlator.key"
echo "  - judge.crt, judge.key"
echo "  - registry-api.crt, registry-api.key"
echo "  - signature-engine.crt, signature-engine.key"
echo "  - frontend.crt, frontend.key"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT SECURITY NOTES:${NC}"
echo "  1. Store ca.key securely (required for certificate renewal)"
echo "  2. Rotate certificates every 90 days (FR-010 compliance)"
echo "  3. Never commit private keys to version control"
echo "  4. Use Kubernetes Secrets or vault for production deployment"
echo ""
echo -e "${YELLOW}📅 Certificate Expiration:${NC}"
openssl x509 -in ca.crt -noout -enddate
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "  1. Copy certificates to service deployments"
echo "  2. Update YAML configs to enable TLS"
echo "  3. Verify mTLS connectivity between services"
echo "  4. Set calendar reminder for 90-day rotation"
echo ""
