"""Create the HTTPS certificate the engine uses on https://localhost.

Writes three files into the given folder:
    ca.crt       a private certificate authority, valid for this purpose only (this is what Windows is asked to trust)
    server.crt   the engine's certificate for "localhost" / 127.0.0.1, signed by that authority
    server.key   the engine's private key
The authority's own private key exists only in memory while this script runs and is never written to disk,
so nothing else can ever be signed with it.

    python make_cert.py <folder>
"""
import datetime
import ipaddress
import os
import sys

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

YEARS = 5


def _usage(**on):
    flags = dict(digital_signature=False, content_commitment=False, key_encipherment=False, data_encipherment=False,
                 key_agreement=False, key_cert_sign=False, crl_sign=False, encipher_only=False, decipher_only=False)
    flags.update(on)
    return x509.KeyUsage(**flags)


def make(folder):
    os.makedirs(folder, exist_ok=True)
    start = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    end = start + datetime.timedelta(days=365 * YEARS + 2)

    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Local Evaluator (this computer only)")])
    ca = (x509.CertificateBuilder()
          .subject_name(ca_name).issuer_name(ca_name).public_key(ca_key.public_key())
          .serial_number(x509.random_serial_number()).not_valid_before(start).not_valid_after(end)
          .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
          .add_extension(_usage(key_cert_sign=True, crl_sign=True), critical=True)
          .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
          .sign(ca_key, hashes.SHA256()))

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cert = (x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]))
            .issuer_name(ca_name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(start).not_valid_after(end)
            .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost"),
                                                        x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(_usage(digital_signature=True, key_encipherment=True), critical=True)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
            .sign(ca_key, hashes.SHA256()))

    pem = serialization.Encoding.PEM
    with open(os.path.join(folder, "ca.crt"), "wb") as fh:
        fh.write(ca.public_bytes(pem))
    with open(os.path.join(folder, "server.crt"), "wb") as fh:
        fh.write(cert.public_bytes(pem))
    with open(os.path.join(folder, "server.key"), "wb") as fh:
        fh.write(key.private_bytes(pem, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
    del ca_key


if __name__ == "__main__":
    make(sys.argv[1])
    print("certificate created")
