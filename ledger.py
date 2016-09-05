from datetime import datetime

from flask import Flask, jsonify, request

app = Flask(__name__)


class DatabaseError(RuntimeError):
    pass


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
            raise DatabaseError('The account "{}" already exists'.format(code))

        self.accounts.append({
            'code': code, 'name': name, 'type': type, 'balance': 0
        })

    def get_account(self, code):
        '''Return the account identified by the specified code.'''
        code = str(code)

        for account in self.accounts:
            if code == account['code']:
                return account
        else:
            return None

    def record_transaction(self, date, description, items):
        '''Record a transaction.'''
        try:
            date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            raise DatabaseError(
                '"{}" is not in the required format "YYYY-MM-DD"'.format(date)
            )

        if sum(item['amount'] for item in items) != 0:
            raise DatabaseError('unbalanced transaction items')

        # Check whether all accounts exist
        for item in items:
            if not self.get_account(item['account_code']):
                raise DatabaseError(
                    'The account "{}" does not exist'.format(
                        item['account_code']
                    )
                )

        self.transactions.append({
            'date': date, 'description': description, 'items': items
        })

        # Update the accounts's balances
        for item in items:
            self.get_account(item['account_code'])['balance'] += item['amount']

        return len(self.transactions)

    def get_transaction(self, id):
        try:
            return self.transactions[id - 1]
        except IndexError:
            return None

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

    try:
        database.create_account(request.json['code'], request.json['name'],
                                request.json['type'])
        return 'Created', 201
    except DatabaseError as exc:
        return str(exc), 409


@app.route('/transactions/<int:id>', methods=['GET'])
def get_transaction(id):
    transaction = database.get_transaction(id)
    if transaction:
        return jsonify({
            'date': transaction['date'].strftime('%Y-%m-%d'),
            'description': transaction['description'],
            'items': transaction['items']
        })
    else:
        return 'Transaction "{}" does not exist'.format(id), 404


@app.route('/transactions', methods=['POST'])
def record_transaction():
    if 'date' not in request.json:
        return 'Missing "date"', 400
    if 'description' not in request.json:
        return 'Missing "description"', 400
    if 'items' not in request.json:
        return 'Missing "items"', 400
    if not request.json['items']:
        return 'Cannot record an empty transaction', 400
    if any('account_code' not in item for item in request.json['items']):
        return 'All items must contain "account_code"', 400
    if any('amount' not in item for item in request.json['items']):
        return 'All items must contain "amount"', 400

    try:
        transaction_id = database.record_transaction(
            request.json['date'],
            request.json['description'],
            request.json['items']
        )
        return str(transaction_id), 201
    except DatabaseError as exc:
        return str(exc), 400


if __name__ == '__main__':
    app.run()
