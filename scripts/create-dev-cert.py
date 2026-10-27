"""python scripts/create-dev-cert.py 192.168.1.20 — CA exclusiva para desenvolvimento."""
from pathlib import Path
import sys,ipaddress,datetime
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
dest=Path(__file__).resolve().parents[1]/'certs-dev';dest.mkdir(exist_ok=True)
if (dest/'ca-key.pem').exists():raise SystemExit('CA já existe. Preserve-a; não será sobrescrita.')
now=datetime.datetime.now(datetime.timezone.utc)
key=rsa.generate_private_key(public_exponent=65537,key_size=3072)
name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'SetRastrear Development CA')])
ca=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(minutes=5)).not_valid_after(now+datetime.timedelta(days=365)).add_extension(x509.BasicConstraints(ca=True,path_length=0),True).add_extension(x509.KeyUsage(digital_signature=True,key_encipherment=False,content_commitment=False,data_encipherment=False,key_agreement=False,key_cert_sign=True,crl_sign=True,encipher_only=False,decipher_only=False),True).sign(key,hashes.SHA256()))
server=rsa.generate_private_key(public_exponent=65537,key_size=3072)
sans=[x509.DNSName('localhost'),x509.IPAddress(ipaddress.ip_address('127.0.0.1')),x509.IPAddress(ipaddress.ip_address('10.0.2.2'))]+[x509.IPAddress(ipaddress.ip_address(a)) for a in sys.argv[1:]]
cert=(x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'localhost')])).issuer_name(name).public_key(server.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(minutes=5)).not_valid_after(now+datetime.timedelta(days=90)).add_extension(x509.SubjectAlternativeName(sans),False).add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),False).sign(key,hashes.SHA256()))
for filename,obj in [('ca-key.pem',key),('server-key.pem',server)]:
 (dest/filename).write_bytes(obj.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
(dest/'ca.pem').write_bytes(ca.public_bytes(serialization.Encoding.PEM));(dest/'ca.crt').write_bytes(ca.public_bytes(serialization.Encoding.DER));(dest/'server.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
print('CA e certificado em certs-dev. Distribua somente ca.crt; proteja as chaves PEM.')
