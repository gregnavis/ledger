from copy import copy
from datetime import datetime
import re


class Ledger(object):
    def __init__(self):
        self.reset()

    def reset(self):
        '''Reset the ledger (for testing purposes).'''
        self.accounts = []
        self.transactions = []

    def create_account(self, code, name, type):
        '''Create an account with a given code and name.'''
        code = str(code)
        name = str(name)

        if self.get_account(code):
            raise LedgerError('The account "{}" already exists'.format(code))

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
        revenues = sum(
            account['balance'] for account in balance_sheet['revenue']
        )
        expenses = sum(
            account['balance'] for account in balance_sheet['expense']
        )
        net_result = revenues - expenses
        if net_result >= 0:
            balance_sheet['net_income'] = net_result
        else:
            balance_sheet['net_loss'] = -net_result
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
            raise LedgerError(
                '"{}" is not in the required format "YYYY-MM-DD"'.format(date)
            )

        if sum(item['amount'] for item in items) != 0:
            raise LedgerError('unbalanced transaction items')

        # Check whether all accounts exist
        for item in items:
            if not self.get_account(item['account_code']):
                raise LedgerError(
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


class LedgerError(RuntimeError):
    pass
