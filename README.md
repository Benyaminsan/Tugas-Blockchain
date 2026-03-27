# Assignment 02. Blockchain Fundamentals


# ⛓️ Fundamental Blockchain dengan Digital Signature & Multi-Node

Tugas ini mengimplementasikan konsep dasar blockchain menggunakan Python dan Flask API.

## 🌟 Fitur Utama
- **Digital Signature (RSA):** Menjamin integritas transaksi. Transaksi hanya valid jika ditandatangani dengan private key pemilik.
- **Miner Reward:** Memberikan insentif otomatis kepada miner sebesar 50 unit setiap kali berhasil menambang block.
- **Consensus Algorithm:** Mekanisme sinkronisasi antar-node menggunakan protokol *Longest Chain*.
- **Multi-Node Simulation:** Dapat dijalankan di beberapa port berbeda untuk mensimulasikan jaringan terdistribusi.

## 🚀 Cara Menjalankan
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
## 1. Cara Menjalankan Node
Buka 3 terminal berbeda dan jalankan perintah berikut:
- **Node 1:** `python blockchain_node.py --port 5000`
- **Node 2:** `python blockchain_node.py --port 5001`
- **Node 3:** `python blockchain_node.py --port 5002`

## 2. Alur Pengujian dengan Postman

### A. Persiapan Identitas (Digital Signature)
Panggil `GET http://localhost:5000/wallet/generate` untuk mendapatkan Private dan Public Key. 
*   **Public Key** akan menjadi alamat "Sender".
*   **Private Key** digunakan untuk menandatangani transaksi (secara internal di logic API, atau gunakan tool luar).

### B. Sinkronisasi Node
Daftarkan Node 2 dan 3 ke Node 1:
- **POST** `http://localhost:5000/nodes/register`
- **Body (JSON):** `{"nodes": ["http://localhost:5001", "http://localhost:5002"]}`

### C. Penambahan Transaksi (Validasi Signature)
- **POST** `http://localhost:5000/transactions/new`
- **Body (JSON):** Masukkan `sender` (Public Key), `receiver`, `amount`, dan `signature`.
- *Catatan:* Jika signature asal-asalan, server akan mengembalikan error 400.

### D. Proses Mining & Reward
- **GET** `http://localhost:5000/mine?miner=ALAMAT_MINER_ANDA`
- Respon akan menunjukkan hash baru dan konfirmasi reward 50 unit.

### E. Konsensus (Sinkronisasi Antar-Node)
Setelah Node 1 menambang, panggil:
- **GET** `http://localhost:5001/nodes/resolve`
- Node 2 sekarang akan memiliki chain yang sama dengan Node 1.

## 3. Screenshot Pengujian