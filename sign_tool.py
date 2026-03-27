# sign_tool.py
import json
import binascii
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256

# 1. Generate Keys
key = RSA.generate(1024)
private_key = binascii.hexlify(key.export_key()).decode()
public_key = binascii.hexlify(key.publickey().export_key()).decode()

# 2. Buat Transaksi
tx_data = {"sender": public_key, "receiver": "Alamat_Bob", "amount": 100}

# 3. Sign Transaksi
hash_obj = SHA256.new(json.dumps(tx_data, sort_keys=True).encode())
signature = binascii.hexlify(pkcs1_15.new(key).sign(hash_obj)).decode()

print(f"--- DATA UNTUK POSTMAN (POST /transactions/new) ---")
print(json.dumps({
    "sender": public_key,
    "receiver": tx_data["receiver"],
    "amount": tx_data["amount"],
    "signature": signature
}, indent=4))
print(f"\n--- PRIVATE KEY (Simpan Rahasia) ---\n{private_key}")