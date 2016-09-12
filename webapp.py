from datetime import datetime
from decimal import Decimal
import locale

from flask import Flask, jsonify, render_template, request

from ledger import Ledger, LedgerError

app = Flask(__name__)


ledger = Ledger()


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
    account = ledger.get_account(code)
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
        ledger.create_account(request.json['code'], request.json['name'],
                              request.json['type'])
        return 'Created', 201
    except LedgerError as exc:
        return str(exc), 409


@app.route('/transactions/<int:id>', methods=['GET'])
def get_transaction(id):
    transaction = ledger.get_transaction(id)
    if transaction:
        return jsonify(_transaction_to_json(transaction))
    else:
        return 'Transaction "{}" does not exist'.format(id), 404


@app.route('/transactions', methods=['GET'])
def get_transactions():
    transactions = ledger.get_transactions()
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
        transaction_id = ledger.record_transaction(
            request.json['date'],
            request.json['description'],
            request.json['items']
        )
        return str(transaction_id), 201
    except LedgerError as exc:
        return str(exc), 400


@app.route('/balance-sheets/<date>.json', methods=['GET'])
def get_json_balance_sheet(date):
    date = datetime.strptime(date, '%Y-%m-%d').date()
    return jsonify(ledger.get_balance_sheet(date))


@app.route('/balance-sheets/<date>.html', methods=['GET'])
def get_html_balance_sheet(date):
    date = datetime.strptime(date, '%Y-%m-%d').date()
    return render_template('balance_sheet.html',
                           balance_sheet=ledger.get_balance_sheet(date))


@app.route('/income-statements/<start_date>-to-<end_date>.json',
           methods=['GET'])
def get_json_income_statement(start_date, end_date):
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    return jsonify(ledger.get_income_statement(start_date, end_date))


@app.route('/income-statements/<start_date>-to-<end_date>.html',
           methods=['GET'])
def get_html_income_statement(start_date, end_date):
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    return render_template(
        'income_statement.html',
        income_statement=ledger.get_income_statement(start_date, end_date)
    )


if __name__ == '__main__':
    app.run()
