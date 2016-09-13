from datetime import date
import unittest
import sqlite3

from ledger import Account, BalanceSheet, IncomeStatement, Ledger, \
    LedgerError, Transaction


class LedgerTestCase(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.ledger = Ledger(self.db)

    def test_create_account(self):
        self.ledger.create_account('101', 'Cash', 'asset')
        self.ledger.create_account('201', 'Bank Loan', 'liability')
        self.ledger.create_account('301', 'Share Capital', 'equity')
        self.ledger.create_account('401', 'Revenue', 'revenue')
        self.ledger.create_account('501', 'Expense', 'expense')

        self.assertEqual(Account('101', 'Cash', 'asset'),
                         self.ledger.get_account('101'))

    def test_create_account_unknown_type(self):
        with self.assertRaises(ValueError):
            self.ledger.create_account('101', 'Cash', 'a')

    def test_create_account_duplicate(self):
        self.ledger.create_account('101', 'Cash', 'asset')

        with self.assertRaises(LedgerError):
            self.ledger.create_account('101', 'Cash', 'asset')

    def test_get_account_non_existent(self):
        self.assertIsNone(self.ledger.get_account('101'))

    def test_record_transaction(self):
        self.ledger.create_account('101', 'Cash', 'asset')
        self.ledger.create_account('301', 'Share Capital', 'equity')

        tx_id = self.ledger.record_transaction(
            date(2016, 9, 1),
            "Record the funder's investment",
            [
                ('101', 500000),
                ('301', -500000)
            ]
        )

        self.assertEqual(Transaction(date(2016, 9, 1),
                                     "Record the funder's investment",
                                     [('101', 500000), ('301', -500000)]),
                         self.ledger.get_transaction(tx_id))

    def test_record_transaction_unknown_account(self):
        with self.assertRaises(ValueError):
            self.ledger.record_transaction(
                date(2016, 9, 1),
                "Record the funder's investment",
                [
                    ('101', 500000),
                    ('301', -500000)
                ]
            )

        self.assertEqual(0, self.ledger.count_transactions())
        self.assertEqual(0, self.ledger.count_transaction_items())

    def test_record_transaction_no_items(self):
        self.ledger.create_account('101', 'Cash', 'asset')
        self.ledger.create_account('301', 'Share Capital', 'equity')

        with self.assertRaises(ValueError):
            self.ledger.record_transaction(
                date(2016, 9, 1),
                "Record the funder's investment",
                []
            )

    def test_get_transaction_non_existent(self):
        self.assertIsNone(self.ledger.get_transaction(1))

    def test_get_transactions(self):
        self.ledger.create_account('101', 'Cash', 'asset')
        self.ledger.create_account('102', 'Equipment', 'asset')
        self.ledger.create_account('301', 'Share Capital', 'equity')
        self.ledger.record_transaction(date(2016, 9, 1),
                                       "Record the funder's investment",
                                       [('101', 500000), ('301', -500000)])
        self.ledger.record_transaction(date(2016, 9, 2),
                                       "Buy a laptop",
                                       [('101', -100000), ('102', 100000)])

        self.assertEqual(
            [
                Transaction(date(2016, 9, 1),
                            "Record the funder's investment",
                            [('101', 500000), ('301', -500000)]),
                Transaction(date(2016, 9, 2),
                            "Buy a laptop",
                            [('101', -100000), ('102', 100000)]),
            ],
            self.ledger.get_transactions()
        )

    def test_get_balance_sheet(self):
        self.ledger.create_account('101', 'Cash', 'asset')
        self.ledger.create_account('102', 'Equipment', 'asset')
        self.ledger.create_account('201', 'Bank Loan', 'liability')
        self.ledger.create_account('301', 'Share Capital', 'equity')
        self.ledger.record_transaction(date(2016, 9, 1),
                                       "Record the funder's investment",
                                       [('101', 500000), ('301', -500000)])
        self.ledger.record_transaction(date(2016, 9, 2),
                                       "Buy a laptop",
                                       [('101', -40000), ('102', 100000),
                                        ('201', -60000)])

        self.assertEqual(
            BalanceSheet(
                date=date(2016, 9, 1),
                asset={
                    Account('101', 'Cash', 'asset'): 500000,
                    Account('102', 'Equipment', 'asset'): 0,
                },
                liability={
                    Account('201', 'Bank Loan', 'liability'): 0,
                },
                equity={
                    Account('301', 'Share Capital', 'equity'): -500000,
                },
            ),
            self.ledger.get_balance_sheet(date(2016, 9, 1))
        )

    def test_get_income_statement(self):
        self.ledger.create_account('101', 'Cash', 'asset')
        self.ledger.create_account('102', 'Equipment', 'asset')
        self.ledger.create_account('201', 'Bank Loan', 'liability')
        self.ledger.create_account('301', 'Share Capital', 'equity')
        self.ledger.create_account('401', 'Consulting Revenue', 'revenue')
        self.ledger.create_account('501', 'Business Travel', 'expense')
        self.ledger.record_transaction(date(2016, 9, 1),
                                       "Record the funder's investment",
                                       [('101', 500000), ('301', -500000)])
        self.ledger.record_transaction(date(2016, 9, 2),
                                       "Buy a laptop",
                                       [('101', -40000), ('102', 100000),
                                        ('201', -60000)])
        self.ledger.record_transaction(date(2016, 9, 4),
                                       "Consulting for Acme, Inc.",
                                       [('101', 1000000), ('401', -1000000)])
        self.ledger.record_transaction(date(2016, 9, 4),
                                       "Travel to Acme, Inc.",
                                       [('101', -150000), ('501', 150000)])
        self.ledger.record_transaction(date(2016, 9, 14),
                                       "Implementation for Acme, Inc.",
                                       [('101', 2500000), ('401', -2500000)])

        self.assertEqual(
            IncomeStatement(
                start_date=date(2016, 9, 1),
                end_date=date(2016, 9, 3),
                revenue={Account('401', 'Consulting Revenue', 'revenue'): 0},
                expense={Account('501', 'Business Travel', 'expense'): 0}
            ),
            self.ledger.get_income_statement(date(2016, 9, 1), date(2016, 9, 3))
        )
        self.assertEqual(
            IncomeStatement(
                start_date=date(2016, 9, 4),
                end_date=date(2016, 9, 13),
                revenue={Account('401', 'Consulting Revenue', 'revenue'): -1000000},
                expense={Account('501', 'Business Travel', 'expense'): 150000}
            ),
            self.ledger.get_income_statement(date(2016, 9, 4), date(2016, 9, 13))
        )


if __name__ == '__main__':
    unittest.main()
