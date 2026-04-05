from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from pathlib import Path

private_key = Ed25519PrivateKey.generate()
public_key = private_key.public_key()
path_file = Path(__file__).resolve().parent
filename = path_file.stem
path_file= path_file
try:
    with open(f"{path_file}/{filename}_privatekey.pem", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    with open(f"{path_file}/{filename}_publickey.pem", "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
    print("Chaves geradas e salvas com sucesso.")
except Exception as e:
    print(f"Erro ao gerar ou salvar as chaves: {e}")