from copy import copy
from datetime import datetime
from decimal import Decimal
import locale
import re

from flask import Flask, jsonify, render_template, request

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

    def get_accounts(self, date):
        '''Return all accounts.'''
        return [self._get_account_at(account, date)
                for account in self.accounts]

    def get_balance_sheet(self, date):
        '''Return a balance sheet.'''
        accounts = self.get_accounts(date)
        balance_sheet = {
            'date': date.strftime('%d.%m.%Y'), 'asset': [], 'liability': [],
            'equity': []
        }
        for account in accounts:
            if account['type'] not in balance_sheet:
                continue
            account = copy(account)
            if account['type'] in ('liability', 'equity'):
                account['balance'] = -account['balance']
            balance_sheet[account['type']].append(account)
        return balance_sheet

    def get_income_statement(self, start_date, end_date):
        '''Return an income statement.'''
        start_accounts = {account['code']: account
                          for account in self.get_accounts(start_date)}
        end_accounts = {account['code']: account
                        for account in self.get_accounts(end_date)}
        balance_sheet = {
            'start_date': start_date.strftime('%d.%m.%Y'),
            'end_date': end_date.strftime('%d.%m.%Y'),
            'revenue': [], 'expense': []
        }
        for code, end_account in end_accounts.iteritems():
            if end_account['type'] not in balance_sheet:
                continue

            start_account = copy(start_accounts[code])
            end_account = copy(end_account)

            if end_account['type'] == 'revenue':
                start_account['balance'] = -start_account['balance']
                end_account['balance'] = -end_account['balance']

            end_account['balance'] -= start_account['balance']

            balance_sheet[end_account['type']].append(end_account)
        return balance_sheet

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

    def get_transactions(self):
        return self.transactions

    def get_transaction(self, id):
        try:
            return self.transactions[id - 1]
        except IndexError:
            return None

    def _get_account_at(self, account, date):
        account = copy(account)
        account.update({
            'balance': sum(
                item['amount']
                for item in self._get_transaction_items(account['code'], date)
            )
        })
        return account

    def _get_transaction_items(self, account_code, date):
        for transaction in self.transactions:
            if transaction['date'] > date:
                continue
            for item in transaction['items']:
                if item['account_code'] == account_code:
                    yield item

database = Database()


def _transaction_to_json(transaction):
    return {
        'date': transaction['date'].strftime('%Y-%m-%d'),
        'description': transaction['description'],
        'items': transaction['items']
    }


@app.template_filter('monetize')
def monetize(value):
    value = Decimal(value) / 100
    locale.setlocale(locale.LC_MONETARY, 'en_US')
    return locale.currency(value, False, True)


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
    allowed_types = ('asset', 'liability', 'equity', 'revenue', 'expense')
    if request.json['type'] not in allowed_types:
        return '"type" must be one of {}'.format(', '.join(allowed_types)), 400

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
        return jsonify(_transaction_to_json(transaction))
    else:
        return 'Transaction "{}" does not exist'.format(id), 404


@app.route('/transactions', methods=['GET'])
def get_transactions():
    transactions = database.get_transactions()
    return jsonify({
        'transactions': [
            _transaction_to_json(transaction) for transaction in transactions
        ]
    })


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


@app.route('/balance-sheets/<date>.json', methods=['GET'])
def get_json_balance_sheet(date):
    date = datetime.strptime(date, '%Y-%m-%d').date()
    return jsonify(database.get_balance_sheet(date))


@app.route('/balance-sheets/<date>.html', methods=['GET'])
def get_html_balance_sheet(date):
    date = datetime.strptime(date, '%Y-%m-%d').date()
    return render_template('balance_sheet.html',
                           balance_sheet=database.get_balance_sheet(date))


@app.route('/income-statements/<start_date>-to-<end_date>.json',
           methods=['GET'])
def get_json_income_statement(start_date, end_date):
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    return jsonify(database.get_income_statement(start_date, end_date))


if __name__ == '__main__':
    app.run()
