r"""
tools/make_signing_key.py
-------------------------
WHY THIS FILE EXISTS:
    Android only accepts an app UPDATE if it is signed with the same key as the installed app.
    This script creates that key ONCE: a "keystore" file (standard PKCS12 format, the same thing
    Java's keytool makes) protected by a long random password.

    The key is saved OUTSIDE the project folder (in C:\Users\<you>\FridgeChef-signing\), so it
    can never be uploaded to GitHub by accident. GitHub Actions gets its own copy through
    encrypted GitHub Secrets.

    !!! NEVER LOSE THE KEYSTORE OR ITS PASSWORD !!!
    Without them you can never publish an update that installs over the existing app.
    Keep a backup copy (e.g. USB stick + Google Drive) and the password in a password manager.

RUN ONCE:   .\.venv\Scripts\python tools\make_signing_key.py
"""

import datetime                                   # the certificate's start and end dates
import os                                         # folders and file paths
import secrets                                    # cryptographically strong random passwords
import sys                                        # exit with a message if the key already exists

from cryptography import x509                     # certificates ("ID cards" for keys)
from cryptography.hazmat.primitives import hashes, serialization   # hashing + saving keys
from cryptography.hazmat.primitives.asymmetric import rsa          # RSA = the key type Android uses
from cryptography.hazmat.primitives.serialization import pkcs12    # the keystore file format
from cryptography.x509.oid import NameOID         # standard field names like "Common Name"

ALIAS = "fridgechef"                              # the key's name inside the keystore
FOLDER = os.path.join(os.path.expanduser("~"), "FridgeChef-signing")   # outside the project!
KEYSTORE = os.path.join(FOLDER, "fridgechef-release.p12")             # the key file itself
PASSWORD_FILE = os.path.join(FOLDER, "PASSWORD - move into a password manager.txt")
YEARS_VALID = 30                                  # Google Play wants keys valid well beyond 2033

if os.path.exists(KEYSTORE):                      # never overwrite: replacing the key would break updates
    sys.exit(f"A keystore already exists: {KEYSTORE}\nKeep using it - do NOT create a new one.")
os.makedirs(FOLDER, exist_ok=True)                # create the private folder

password = secrets.token_urlsafe(24)              # 32 random letters/digits - impossible to guess
private_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)   # the secret key

name = x509.Name([                                # who the key belongs to (shown inside the APK)
    x509.NameAttribute(NameOID.COMMON_NAME, "FridgeChef"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "FridgeChef"),
    x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
])
now = datetime.datetime.now(datetime.timezone.utc)
certificate = (                                   # a "self-signed" certificate = the key vouches for itself
    x509.CertificateBuilder()
    .subject_name(name).issuer_name(name)         # owner and issuer are the same (normal for Android)
    .public_key(private_key.public_key())         # the public half, which everyone may see
    .serial_number(x509.random_serial_number())   # a unique number for this certificate
    .not_valid_before(now)                        # valid from now...
    .not_valid_after(now + datetime.timedelta(days=365 * YEARS_VALID))   # ...for 30 years
    .sign(private_key, hashes.SHA256())           # sign it with the secret key
)

# Save as PKCS12 using the classic, universally supported encryption (Java/Android read it fine).
encryption = (serialization.PrivateFormat.PKCS12.encryption_builder()
              .kdf_rounds(50000)                                           # slows down guessing attacks
              .key_cert_algorithm(pkcs12.PBES.PBESv1SHA1And3KeyTripleDESCBC)   # widely compatible
              .hmac_hash(hashes.SHA1())
              .build(password.encode()))
data = pkcs12.serialize_key_and_certificates(
    name=ALIAS.encode(), key=private_key, cert=certificate, cas=None, encryption_algorithm=encryption)
with open(KEYSTORE, "wb") as f:                   # "wb" = write bytes
    f.write(data)
with open(PASSWORD_FILE, "w", encoding="utf-8") as f:
    f.write(f"Keystore: {KEYSTORE}\nAlias: {ALIAS}\nPassword: {password}\n\n"
            "Move this password into a password manager, back up the .p12 file, then delete this text file.\n")

check = pkcs12.load_key_and_certificates(data, password.encode())   # read it back to prove it works
fingerprint = check[1].fingerprint(hashes.SHA256()).hex(":").upper()
print("Keystore created:", KEYSTORE)
print("Alias:", ALIAS, "| valid until:", certificate.not_valid_after_utc.date())
print("Certificate SHA-256 fingerprint:", fingerprint)
print("Password saved in:", PASSWORD_FILE)
