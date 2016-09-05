from flask import Flask, jsonify, request

app = Flask(__name__)


class Database(object):
    def __init__(self):
        self.reset()

    def reset(self):
        '''Reset the database (for testing purposes).'''
        self.accounts = []
        self.transactions = []

    def create_account(self, code, name, type):
        '''Create an account with a given code and name.'''
        code = str(code)
        name = str(name)

        if self.get_account(code):
            return False

        self.accounts.append({
            'code': code, 'name': name, 'type': type, 'balance': 0
        })
        return True

    def get_account(self, code):
        '''Return the account identified by the specified code.'''
        code = str(code)

        for account in self.accounts:
            if code == account['code']:
                return account
        else:
            return None

    def record_transaction(self, date, description, items):
        '''Record a transcation.'''
        if sum(item['amount'] for item in items) != 0:
            return False

        # Check whether all accounts exist
        for item in items:
            if not self.get_account(item['account_code']):
                return False

        self.transactions.append({
            'date': date, 'description': description, 'items': items
        })

        # Update the accounts's balances
        for item in items:
            self.get_account(item['account_code'])['balance'] += item['amount']

        return True

database = Database()


@app.route('/accounts/<code>', methods=['GET'])
def get_account(code):
    account = database.get_account(code)
    if account:
        return jsonify(account)
    else:
        return 'Account "{}" does not exist'.format(code), 404


@app.route('/accounts', methods=['POST'])
def create_account():
    if request.json is None:
        return 'Expected JSON-encoded data', 400
    if 'name' not in request.json:
        return 'Missing "name"', 400
    if 'code' not in request.json:
        return 'Missing "code"', 400
    if 'type' not in request.json:
        return 'Missing "type"', 400
    if request.json['type'] not in ('asset', 'liability', 'equity'):
        return '"type" must be one of "asset", "liability", "equity"', 400

    if database.create_account(request.json['code'], request.json['name'],
                               request.json['type']):
        return 'Created', 201
    else:
        return 'Account "{}" already exists'.format(request.json['code']), 409


@app.route('/transactions', methods=['POST'])
def record_transaction():
    if not request.json['items']:
        return 'Cannot record an empty transaction', 400

    database.record_transaction(request.json['date'],
                                request.json['description'],
                                request.json['items'])
    return 'Recorded', 201


if __name__ == '__main__':
    app.run()
