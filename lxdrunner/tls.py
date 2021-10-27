import datetime
import getpass
import platform
import ssl
from urllib.parse import urlparse

import pylxd
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from . import lxd
from .appconf import config as cfg
from .applog import log


def gen_priv_key():
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    return key


def gen_pub_key(key):
    # Various details about who we are. For a self-signed certificate the
    # subject and issuer are always the same.
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u""),
            x509.NameAttribute(NameOID.LOCALITY_NAME, u""),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"LXDRunner"),
            x509.NameAttribute(
                NameOID.COMMON_NAME, f"lxdrunner@{platform.node()}"
            ),
        ]
    )

    cert = x509.CertificateBuilder(
    ).subject_name(subject).issuer_name(issuer).public_key(
        key.public_key()
    ).serial_number(x509.random_serial_number()).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(

        # Our certificate will be valid for 10 days
        datetime.datetime.utcnow() + datetime.timedelta(days=10)
    ).add_extension(
        x509.SubjectAlternativeName([x509.DNSName(u"localhost")]),
        critical=False,

        # Sign our certificate with our private key
    ).sign(key, hashes.SHA256())

    return cert


def gen_key_pair():
    " Generate client key pair and save to disk "
    (crt_path, key_path) = cfg.key_pair_paths()

    if crt_path.exists():
        return

    log.info("Generating key pair")

    key = gen_priv_key()
    cert = gen_pub_key(key)
    with key_path.open("wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    with crt_path.open("wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))


def authenticate(client):
    " Authenticate with remote LXD server"
    while not client.trusted:
        trust_pass = getpass.getpass(prompt="Trust Password:")
        try:
            client.authenticate(trust_pass)
        except pylxd.exceptions.LXDAPIException as err:
            if str(err) != 'not authorized':
                raise
            log.error("Authentication Error")


def get_peer_cert(host, port):
    " Get cert from server "
    pemcert = ssl.get_server_certificate((host, port))
    return pemcert


def show_fingerprint(pemcert):
    " Show cert subject and fingerprint "
    pemutf = pemcert.encode('utf-8')
    cert = x509.load_pem_x509_certificate(pemutf, default_backend())
    print("Subject:", cert.subject.rfc4514_string())
    print(
        "Fingerprint:",
        cert.fingerprint(cert.signature_hash_algorithm).hex()
    )


def confirm_accept_peer():
    res = input("Accept remote y/n : ")
    if res.startswith('y'):
        return True
    return False


def confirm_certs():
    " Confirm all LXD remotes "
    for rname, remote in cfg.remotes.items():
        path = cfg.dirs.servcerts / f"{rname}.crt"
        if not (
            remote.protocol == 'lxd' and remote.addr
            and "https://" in remote.addr
        ):
            continue
        if not path.exists():
            url = urlparse(remote.addr)
            host = url.netloc
            port = 443
            if ":" in url.netloc:
                host, port = url.netloc.split(":")
            pem = get_peer_cert(host, port)
            show_fingerprint(pem)
            if not confirm_accept_peer():
                continue
            # FIX TLS VERIFICATION
            client = lxd.get_client(rname, verify=False)
            authenticate(client)
            with path.open("wb") as certfile:
                certfile.write(pem.encode('utf-8'))
