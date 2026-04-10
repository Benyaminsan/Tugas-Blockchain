import hashlib
import json
import datetime
import requests
from flask import Flask, jsonify, request
from urllib.parse import urlparse
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import binascii

class Transaction:
    def __init__(self, sender, receiver, amount, signature=None):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.signature = signature

    def to_dict(self, include_signature=True):
        """Mengembalikan dict transaksi. Signature dipisahkan agar hash tetap konsisten."""
        data = {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount
        }
        if include_signature and self.signature:
            data["signature"] = self.signature
        return data

    def is_valid(self):
        """Memverifikasi signature. Harus cocok dengan cara sign_tool.py bekerja."""
        if self.sender == "Network": # Reward dari sistem selalu valid
            return True
        if not self.signature:
            return False
        
        try:
            # Data yang di-hash harus SAMA dengan di sign_tool.py
            # Yaitu hanya sender, receiver, dan amount
            hash_data = {
                "sender": self.sender,
                "receiver": self.receiver,
                "amount": self.amount
            }
            public_key = RSA.import_key(binascii.unhexlify(self.sender))
            transaction_data = json.dumps(hash_data, sort_keys=True).encode()
            hash_obj = SHA256.new(transaction_data)
            
            pkcs1_15.new(public_key).verify(hash_obj, binascii.unhexlify(self.signature))
            return True
        except (ValueError, TypeError):
            return False

class Block:
    def __init__(self, index, transactions, previous_hash, nonce=0):
        self.index = index
        self.timestamp = str(datetime.datetime.now())
        self.transactions = transactions
        self.nonce = nonce
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_content = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [t.to_dict() for t in self.transactions],
            "nonce": self.nonce,
            "previous_hash": self.previous_hash,
        }
        block_string = json.dumps(block_content, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty):
        while self.hash[:difficulty] != "0" * difficulty:
            self.nonce += 1
            self.hash = self.calculate_hash()

class Blockchain:
    def __init__(self):
        self.chain = [self.init_genesis_block()]
        self.difficulty = 3
        self.pending_transactions = []
        self.mining_reward = 50
        self.nodes = set()

    def init_genesis_block(self):
        return Block(0, [], "0")

    def register_node(self, address):
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)

    def add_transaction(self, transaction):
        if not transaction.is_valid():
            return False
        self.pending_transactions.append(transaction)
        return True

    def mine_pending_transactions(self, miner_address):
        # Tambahkan reward (Tanpa signature karena sender="Network")
        reward_tx = Transaction("Network", miner_address, self.mining_reward, None)
        self.pending_transactions.append(reward_tx)

        new_block = Block(len(self.chain), self.pending_transactions, self.chain[-1].hash)
        new_block.mine_block(self.difficulty)
        
        self.chain.append(new_block)
        self.pending_transactions = []
        return new_block

    def resolve_conflicts(self):
        """Konsensus: Mengambil chain terpanjang dari jaringan."""
        neighbours = self.nodes
        new_chain = None
        max_length = len(self.chain)

        for node in neighbours:
            try:
                response = requests.get(f'http://{node}/chain', timeout=5)
                if response.status_code == 200:
                    length = response.json()['length']
                    chain = response.json()['chain']
                    if length > max_length:
                        max_length = length
                        new_chain = chain
            except:
                continue
        
        if new_chain:
            self.chain = []
            for b in new_chain:
                # Memastikan constructor Transaction dipanggil dengan 4 argumen
                txs = [Transaction(t['sender'], t['receiver'], t['amount'], t.get('signature')) for t in b['transactions']]
                block = Block(b['index'], txs, b['previous_hash'], b['nonce'])
                block.timestamp = b['timestamp']
                block.hash = b['hash']
                self.chain.append(block)
            return True
        return False

# --- FLASK API ---
app = Flask(__name__)
blockchain = Blockchain()

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ['sender', 'receiver', 'amount', 'signature']
    if not all(k in values for k in required):
        return 'Data tidak lengkap', 400
    
    tx = Transaction(values['sender'], values['receiver'], values['amount'], values['signature'])
    if blockchain.add_transaction(tx):
        return jsonify({'message': 'Berhasil! Transaksi masuk ke pool.'}), 201
    return jsonify({'message': 'Gagal! Signature digital tidak valid.'}), 400

@app.route('/mine', methods=['GET'])
def mine():
    miner_addr = request.args.get('miner')
    if not miner_addr:
        return "Butuh alamat miner untuk reward", 400
    block = blockchain.mine_pending_transactions(miner_addr)
    return jsonify({
        'message': "Block baru berhasil ditambang!",
        'index': block.index,
        'hash': block.hash,
        'reward': blockchain.mining_reward
    }), 200

@app.route('/chain', methods=['GET'])
def full_chain():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append({
            'index': block.index,
            'timestamp': block.timestamp,
            'transactions': [t.to_dict() for t in block.transactions],
            'nonce': block.nonce,
            'previous_hash': block.previous_hash,
            'hash': block.hash
        })
    return jsonify({'chain': chain_data, 'length': len(chain_data)}), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')
    for node in nodes:
        blockchain.register_node(node)
    return jsonify({'message': 'Node berhasil terhubung', 'total_nodes': list(blockchain.nodes)}), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()
    if replaced:
        return jsonify({'message': 'Chain diperbarui (mengikuti yang terpanjang)'}), 200
    return jsonify({'message': 'Chain sudah sinkron'}), 200

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port')
    args = parser.parse_args()
    app.run(host='0.0.0.0', port=args.port)