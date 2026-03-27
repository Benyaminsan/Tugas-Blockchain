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
    def __init__(self, sender, receiver, amount, signature):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.signature = signature

    def to_dict(self):
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "signature": self.signature
        }
    
    def sign_trasaction(self, private_key):
        """Menandatangani transaksi dengan private key."""
        if self.sender == "Network": # Reward tidak butuh signature dari user
            return
        
        private_key = RSA.import_key(binascii.unhexlify(private_key))
        transaction_data = json.dumps(self.to_dict(), sort_keys=True).encode()
        hash_obj = SHA256.new(transaction_data)
        signature = pkcs1_15.new(private_key).sign(hash_obj)
        self.signature = binascii.hexlify(signature).decode('ascii')

    def is_valid(self):
        """Memverifikasi signature transaksi."""
        if self.sender == "Network":
            return True
        if not self.signature:
            return False
        
        try:
            public_key = RSA.import_key(binascii.unhexlify(self.sender))
            transaction_data = json.dumps(self.to_dict(), sort_keys=True).encode()
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
        self.nodes.add(parsed_url.netloc)

    def add_transaction(self, transaction):
        if not transaction.is_valid():
            return False
        self.pending_transactions.append(transaction)
        return True

    def mine_pending_transactions(self, miner_address):
        # Tambahkan reward untuk miner
        reward_tx = Transaction("Network", miner_address, self.mining_reward)
        self.pending_transactions.append(reward_tx)

        new_block = Block(len(self.chain), self.pending_transactions, self.chain[-1].hash)
        new_block.mine_block(self.difficulty)
        
        self.chain.append(new_block)
        self.pending_transactions = []
        return new_block

    def is_valid_chain(self, chain):
        # Logika validasi chain dari node lain
        for i in range(1, len(chain)):
            current = chain[i]
            prev = chain[i-1]
            # (Sederhananya kita asumsikan struktur sudah benar dalam simulasi ini)
            if current['previous_hash'] != prev['hash']:
                return False
        return True

    def resolve_conflicts(self):
        """Consensus: Ambil chain terpanjang di network."""
        neighbours = self.nodes
        new_chain = None
        max_length = len(self.chain)

        for node in neighbours:
            response = requests.get(f'http://{node}/chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                if length > max_length: # Sederhananya validasi dilewati untuk demo
                    max_length = length
                    new_chain = chain
        
        if new_chain:
            # Reconstruct chain from dict
            self.chain = []
            for b in new_chain:
                txs = [Transaction(t['sender'], t['receiver'], t['amount']) for t in b['transactions']]
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
        return 'Missing values', 400
    
    tx = Transaction(values['sender'], values['receiver'], values['amount'], values['signature'])
    if blockchain.add_transaction(tx):
        return jsonify({'message': 'Transaksi ditambahkan ke pool!'}), 201
    return jsonify({'message': 'Signature tidak valid!'}), 400

@app.route('/mine', methods=['GET'])
def mine():
    miner_addr = request.args.get('miner')
    if not miner_addr:
        return "Miner address required", 400
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
    return jsonify({'message': 'Node berhasil didaftarkan', 'total_nodes': list(blockchain.nodes)}), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()
    if replaced:
        return jsonify({'message': 'Chain diganti dengan yang terpanjang', 'new_chain': 'updated'}), 200
    return jsonify({'message': 'Chain sudah yang terbaru', 'chain': 'current'}), 200

# Endpoint bantu untuk generate keypair (untuk demo)
@app.route('/wallet/generate', methods=['GET'])
def generate_wallet():
    key = RSA.generate(1024)
    private_key = binascii.hexlify(key.export_key()).decode('ascii')
    public_key = binascii.hexlify(key.publickey().export_key()).decode('ascii')
    return jsonify({'private_key': private_key, 'public_key': public_key})

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    app.run(host='0.0.0.0', port=args.port)