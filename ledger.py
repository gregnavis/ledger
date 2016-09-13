from collections import namedtuple
from copy import copy
from datetime import datetime
import re
import sqlite3


class Ledger(object):
    ACCOUNT_TYPES = ('asset', 'liability', 'equity', 'revenue', 'expense')

    def __init__(self, database):
        self.db = database

    def init(self):
        '''Initialize the database.'''
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS accounts(
            code VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            type VARCHAR(255) NOT NULL
        );
        CREATE TABLE IF NOT EXISTS transactions(
            id INTEGER PRIMARY KEY,
            date VARCHAR(255) NOT NULL,
            description VARCHAR(255) NOT NULL
        );
        CREATE TABLE IF NOT EXISTS transaction_items(
            id INTEGER PRIMARY KEY,
            transaction_id INTEGER NOT NULL REFERENCES transactions(id),
            account_code VARCHAR(255) NOT NULL REFERENCES accounts(code),
            amount INTEGER NOT NULL
        );
        ''')
        self.db.commit()

    def drop(self):
        '''Reset the ledger.'''
        self.db.executescript('''
        DROP TABLE IF EXISTS transaction_items;
        DROP TABLE IF EXISTS transactions;
        DROP TABLE IF EXISTS accounts;
        ''')
        self.db.commit()

    def reset(self):
        '''Reset the ledger.'''
        self.drop()
        self.init()

    def create_account(self, code, name, type):
        '''Create an account with a given code and name.'''
        if type not in self.ACCOUNT_TYPES:
            raise ValueError('unknown account type {}'.format(type))
        if self.get_account(code):
            raise LedgerError('The account "{}" already exists'.format(code))
        self.db.execute(
            'INSERT INTO accounts(code, name, type) VALUES (?, ?, ?)',
            (code, name, type)
        ).close()
        self.db.commit()

    def get_balance_sheet(self, date):
        '''Return a balance sheet.'''
        rows = self.db.execute('''
        SELECT
            a.code, a.name, a.type, SUM(
                CASE
                    WHEN date(t.date) <= date(?) THEN ti.amount
                    ELSE 0
                END
            )
            FROM accounts a
            LEFT JOIN transaction_items ti ON a.code = ti.account_code
            LEFT JOIN transactions t ON ti.transaction_id = t.id
            GROUP BY a.code
        ''', (date,)).fetchall()

        retained_earnings = 0
        accounts_by_type = {'asset': {}, 'liability': {}, 'equity': {}}
        for code, name, type, balance in rows:
            if type in ('revenue', 'expense'):
                retained_earnings -= balance
            else:
                accounts_by_type[type][Account(code, name, type)] = balance

        return BalanceSheet(
            date=date,
            retained_earnings=retained_earnings,
            **accounts_by_type
        )

    def get_income_statement(self, start_date, end_date):
        '''Return an income statement.'''
        rows = self.db.execute('''
        SELECT
            a.code, a.name, a.type, SUM(
                CASE
                    WHEN date(?) <= date(t.date) AND date(t.date) <= date(?)
                        THEN ti.amount
                    ELSE 0
                END
            )
            FROM accounts a
            LEFT JOIN transaction_items ti ON a.code = ti.account_code
            LEFT JOIN transactions t ON ti.transaction_id = t.id
            WHERE a.type IN ("revenue", "expense")
            GROUP BY a.code
        ''', (start_date, end_date)).fetchall()

        accounts_by_type = {'revenue': {}, 'expense': {}}
        for code, name, type, balance in rows:
            accounts_by_type[type][Account(code, name, type)] = balance

        return IncomeStatement(
            start_date=start_date,
            end_date=end_date,
            **accounts_by_type
        )

    def get_account(self, code):
        '''Return the account identified by the specified code.'''
        row = self.db.execute('SELECT * FROM accounts WHERE code = ?',
                              (code,)).fetchone()
        if row is None:
            return None
        return Account(row[0], row[1], row[2])

    def record_transaction(self, date, description, items):
        '''Record a transaction.'''
        if not items:
            raise ValueError('cannot record an empty transaction')
        if sum(item[1] for item in items) != 0:
            raise ValueError('unbalanced transaction items')

        try:
            c = self.db.cursor()
            c.execute(
                'INSERT INTO transactions(date, description) VALUES (?, ?)',
                (date.strftime('%Y-%m-%d'), description)
            )
            tx_id = c.lastrowid

            for account_code, amount in items:
                c.execute(
                    'SELECT 1 FROM accounts WHERE code = ?',
                    (account_code,)
                )
                if c.fetchone() is None:
                    raise ValueError(
                        'unknown account code {}'.format(account_code)
                    )
                c.execute('''INSERT INTO transaction_items(transaction_id,
                                                           account_code,
                                                           amount)
                                                           VALUES (?, ?, ?)''',
                          (tx_id, account_code, amount))
        except:
            self.db.rollback()
            raise
        finally:
            c.close()

        self.db.commit()
        return tx_id

    def count_transactions(self):
        '''Return the number of transactions.'''
        return self.db.execute(
            'SELECT COUNT(*) FROM transactions'
        ).fetchone()[0]

    def count_transaction_items(self):
        '''Return the number of transaction items.'''
        return self.db.execute(
            'SELECT COUNT(*) FROM transaction_items'
        ).fetchone()[0]

    def get_transactions(self):
        '''Return all registered transactions.'''
        txs = {}

        rows = self.db.execute('SELECT * FROM transactions').fetchall()
        for tx_id, date, description in rows:
            date = datetime.strptime(date, '%Y-%m-%d').date()
            txs[tx_id] = Transaction(date, description, [])

        rows = self.db.execute('SELECT * FROM transaction_items').fetchall()
        for _, tx_id, account_code, amount in rows:
            txs[tx_id].items.append((account_code, amount))

        return txs.values()

    def get_transaction(self, tx_id):
        '''Return the specified transaction.'''
        row = self.db.execute('SELECT * FROM transactions WHERE id = ?',
                              (tx_id,)).fetchone()
        if row is None:
            return None

        date = datetime.strptime(row[1], '%Y-%m-%d').date()
        description = row[2]

        items = []
        rows = self.db.execute(
            'SELECT * FROM transaction_items WHERE transaction_id = ?',
            (tx_id,)
        ).fetchall()
        for row in rows:
            items.append((row[2], row[3]))

        return Transaction(date, description, items)


class LedgerError(RuntimeError):
    pass


Account = namedtuple('Account', 'code name type')
Transaction = namedtuple('Transaction', 'date description items')


class BalanceSheet(namedtuple('BalanceSheet',
                              'date asset liability equity retained_earnings')):
    @property
    def total_assets(self):
        return sum(self.asset.itervalues())

    @property
    def total_liabilities(self):
        return -sum(self.liability.itervalues())

    @property
    def total_equity(self):
        return -sum(self.equity.itervalues()) + self.retained_earnings


class IncomeStatement(namedtuple('_IncomeStatement',
                                 'start_date end_date revenue expense')):
    @property
    def total_revenues(self):
        return -sum(self.revenue.itervalues())

    @property
    def total_expenses(self):
        return sum(self.expense.itervalues())

    @property
    def net_result(self):
        return self.total_revenues - self.total_expenses

    @property
    def net_income(self):
        if self.net_result >= 0:
            return self.net_result
        return 0

    @property
    def net_loss(self):
        if self.net_result < 0:
            return - self.net_result
        return 0
