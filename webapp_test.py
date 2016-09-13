import json
import unittest

import webapp


class WebAppTestCase(unittest.TestCase):
    def setUp(self):
        webapp.app.config['TESTING'] = True
        webapp.app.config['DATABASE_URL'] = 'test.sqlite3'
        self.app = webapp.app.test_client()
        with webapp.app.app_context():
            webapp.reset_ledger()

    def test_create_account_and_get_account(self):
        with webapp.app.app_context():
            response = self._create_account('101', 'Cash', 'asset')

            self.assertEqual(201, response.status_code)

            response = self.app.get('/accounts/101')

            self.assertEqual(200, response.status_code)
            self.assertEqual('application/json', response.content_type)
            self.assertJson(
                {'name': 'Cash', 'code': '101', 'type': 'asset'},
                response
            )

    def test_create_account_incomplete(self):
        self.assertEqual(
            400, self._create_account(None, 'Cash', 'asset').status_code
        )
        self.assertEqual(
            400, self._create_account('101', None, 'asset').status_code
        )
        self.assertEqual(
            400, self._create_account('101', 'Cash', None).status_code
        )

    def test_create_account_twice(self):
        with webapp.app.app_context():
            self._create_account('101', 'Cash', 'asset')

            self.assertEqual(
                409,
                self._create_account('101', 'Cash', 'asset').status_code
            )

    def test_create_account_invalid(self):
        self.assertEqual(400,
                         self._create_account('101', 'Cash', 'a').status_code)

    def test_create_account_not_json(self):
        self.assertEqual(
            400,
            self.app.post('/accounts',
                          data={'code': '101', 'name': 'Cash'}).status_code
        )

    def test_get_account_non_existent(self):
        self.assertEqual(404, self._get_account('101').status_code)

    def test_record_transaction(self):
        with webapp.app.app_context():
            self._create_account('101', 'Cash', 'asset')
            self._create_account('320', 'Share Capital', 'equity')

            response = self._record_transaction(
                '2016-09-01',
                "Record the founder's investment",
                [
                    {'account_code': '101', 'amount': 10000},
                    {'account_code': '320', 'amount': -10000}
                ]
            )

            self.assertEqual(201, response.status_code)

            response = self._get_transaction(int(response.get_data()))

            self.assertEqual(200, response.status_code)
            self.assertJson(
                {
                    'date': '2016-09-01',
                    'description': "Record the founder's investment",
                    'items': [
                        {'account_code': '101', 'amount': 10000},
                        {'account_code': '320', 'amount': -10000},
                    ]
                },
                response
            )

    def test_record_transaction_empty(self):
        self._create_account('101', 'Cash', 'asset')
        self._create_account('320', 'Share Capital', 'equity')

        response = self._record_transaction('2016-09-01',
                                            'An empty transaction', [])

        self.assertEqual(400, response.status_code)

    def test_record_unbalanced_transaction(self):
        self._create_account('101', 'Cash', 'asset')
        self._create_account('320', 'Share Capital', 'equity')

        response = self._record_transaction(
            '2016-09-01',
            "Record the founder's investment",
            [
                {'account_code': '101', 'amount': 10000},
                {'account_code': '320', 'amount': -9999}
            ]
        )

        self.assertEqual(400, response.status_code)

    def test_record_transaction_incomplete(self):
        self._create_account('101', 'Cash', 'asset')
        self._create_account('320', 'Share Capital', 'equity')

        response = self._post_json('/transactions', {
            'description': "Record the founder's investment",
            'items': [
                {'account_code': '101', 'amount': 10000},
                {'account_code': '320', 'amount': -10000}
            ]
        })
        self.assertEqual(400, response.status_code)

        response = self._post_json('/transactions', {
            'date': '2016-09-01',
            'items': [
                {'account_code': '101', 'amount': 10000},
                {'account_code': '320', 'amount': -10000}
            ]
        })
        self.assertEqual(400, response.status_code)

        response = self._post_json('/transactions', {
            'date': '2016-09-01',
            'description': "Record the founder's investment",
        })
        self.assertEqual(400, response.status_code)

        response = self._post_json('/transactions', {
            'date': '2016-09-01',
            'description': "Record the founder's investment",
            'items': [
                {'account_code': '101', 'amount': 10000},
                {'amount': -10000}
            ]
        })
        self.assertEqual(400, response.status_code)

        response = self._post_json('/transactions', {
            'date': '2016-09-01',
            'description': "Record the founder's investment",
            'items': [
                {'account_code': '101', 'amount': 10000},
                {'account_code': '320'}
            ]
        })
        self.assertEqual(400, response.status_code)

    def test_record_transaction_invalid_date(self):
        response = self._record_transaction(
            '20160901',
            "Record the founder's investment",
            [
                {'account_code': '101', 'amount': 10000},
                {'account_code': '320', 'amount': -10000}
            ]
        )
        self.assertEqual(400, response.status_code)

    def test_get_transactions(self):
        with webapp.app.app_context():
            self._create_account('101', 'Cash', 'asset')
            self._create_account('102', 'Equipment', 'asset')
            self._create_account('320', 'Share Capital', 'equity')
            self._record_transaction(
                '2016-09-01',
                "Record the founder's investment",
                [
                    {'account_code': '101', 'amount': 10000},
                    {'account_code': '320', 'amount': -10000}
                ]
            )
            self._record_transaction(
                '2016-09-02',
                "Buy a computer",
                [
                    {'account_code': '101', 'amount': -2000},
                    {'account_code': '102', 'amount': 2000}
                ]
            )

            response = self.app.get('/transactions')
            self.assertEqual(200, response.status_code)
            self.assertJson(
                {
                    'transactions': [
                        {
                            'date': '2016-09-01',
                            'description': "Record the founder's investment",
                            'items': [
                                {'account_code': '101', 'amount': 10000},
                                {'account_code': '320', 'amount': -10000}
                            ],
                        },
                        {
                            'date': '2016-09-02',
                            'description': "Buy a computer",
                            'items': [
                                {'account_code': '101', 'amount': -2000},
                                {'account_code': '102', 'amount': 2000}
                            ],
                        }
                    ]
                },
                response
            )

    def test_get_transaction_non_existent(self):
        self._create_account('101', 'Cash', 'asset')
        self._create_account('320', 'Share Capital', 'equity')
        response = self.app.get('/transactions/1')
        self.assertEqual(404, response.status_code)

    def test_get_balance_sheet(self):
        with webapp.app.app_context():
            self._create_account('101', 'Cash', 'asset')
            self._create_account('102', 'Equipment', 'asset')
            self._create_account('201', 'Bank Loan', 'liability')
            self._create_account('320', 'Share Capital', 'equity')
            self._create_account('401', 'Revenue', 'revenue')
            self._create_account('501', 'Expense', 'expense')
            self._record_transaction(
                '2016-09-01',
                "Record the founder's investment",
                [
                    {'account_code': '101', 'amount': 10000},
                    {'account_code': '320', 'amount': -10000}
                ]
            )
            self._record_transaction(
                '2016-09-10',
                "Buy a computer",
                [
                    {'account_code': '102', 'amount': 2000},
                    {'account_code': '101', 'amount': -500},
                    {'account_code': '201', 'amount': -1500},
                ]
            )

            response = self.app.get('/balance-sheets/2016-09-09.json')
            self.assertEqual(200, response.status_code)
            self.assertJson(
                {
                    'date': '09.09.2016',
                    'asset': [
                        {
                            'code': '101',
                            'name': 'Cash',
                            'type': 'asset',
                            'balance': 10000
                        },
                        {
                            'code': '102',
                            'name': 'Equipment',
                            'type': 'asset',
                            'balance': 0
                        },
                    ],
                    'liability': [
                        {
                            'code': '201',
                            'name': 'Bank Loan',
                            'type': 'liability',
                            'balance': 0
                        }
                    ],
                    'equity': [
                        {
                            'code': '320',
                            'name': 'Share Capital',
                            'type': 'equity',
                            'balance': 10000
                        }
                    ]
                },
                response
            )

            response = self.app.get('/balance-sheets/2016-09-10.json')
            self.assertEqual(200, response.status_code)
            self.assertJson(
                {
                    'date': '10.09.2016',
                    'asset': [
                        {
                            'code': '101',
                            'name': 'Cash',
                            'type': 'asset',
                            'balance': 9500
                        },
                        {
                            'code': '102',
                            'name': 'Equipment',
                            'type': 'asset',
                            'balance': 2000
                        },
                    ],
                    'liability': [
                        {
                            'code': '201',
                            'name': 'Bank Loan',
                            'type': 'liability',
                            'balance': 1500
                        }
                    ],
                    'equity': [
                        {
                            'code': '320',
                            'name': 'Share Capital',
                            'type': 'equity',
                            'balance': 10000
                        }
                    ]
                },
                response
            )

            self._record_transaction(
                '2016-09-11',
                "Software consulting for Acme Inc.",
                [
                    {'account_code': '101', 'amount': 5000},
                    {'account_code': '401', 'amount': -5000},
                ]
            )
            self._record_transaction(
                '2016-09-11',
                "Business travel",
                [
                    {'account_code': '101', 'amount': -500},
                    {'account_code': '501', 'amount': 500},
                ]
            )

            response = self.app.get('/balance-sheets/2016-09-11.json')
            self.assertEqual(200, response.status_code)
            self.assertJson(
                {
                    'date': '11.09.2016',
                    'asset': [
                        {
                            'code': '101',
                            'name': 'Cash',
                            'type': 'asset',
                            'balance': 14000
                        },
                        {
                            'code': '102',
                            'name': 'Equipment',
                            'type': 'asset',
                            'balance': 2000
                        },
                    ],
                    'liability': [
                        {
                            'code': '201',
                            'name': 'Bank Loan',
                            'type': 'liability',
                            'balance': 1500
                        }
                    ],
                    'equity': [
                        {
                            'code': '320',
                            'name': 'Share Capital',
                            'type': 'equity',
                            'balance': 10000
                        }
                    ]
                },
                response
            )

    def test_get_income_statement(self):
        with webapp.app.app_context():
            self._create_account('101', 'Cash', 'asset')
            self._create_account('102', 'Equipment', 'asset')
            self._create_account('201', 'Bank Loan', 'liability')
            self._create_account('320', 'Share Capital', 'equity')
            self._create_account('401', 'Revenue', 'revenue')
            self._create_account('501', 'Expense', 'expense')
            self._record_transaction(
                '2016-09-01',
                "Record the founder's investment",
                [
                    {'account_code': '101', 'amount': 10000},
                    {'account_code': '320', 'amount': -10000}
                ]
            )
            self._record_transaction(
                '2016-09-10',
                "Buy a computer",
                [
                    {'account_code': '102', 'amount': 2000},
                    {'account_code': '101', 'amount': -500},
                    {'account_code': '201', 'amount': -1500},
                ]
            )
            self._record_transaction(
                '2016-09-11',
                'Software consulting for Acme Inc.',
                [
                    {'account_code': '101', 'amount': 5000},
                    {'account_code': '401', 'amount': -5000},
                ]
            )
            self._record_transaction(
                '2016-09-11',
                'Business Travel',
                [
                    {'account_code': '101', 'amount': -400},
                    {'account_code': '501', 'amount': 400},
                ]
            )
            self._record_transaction(
                '2016-09-12',
                'Insurance Premiums',
                [
                    {'account_code': '101', 'amount': -5200},
                    {'account_code': '501', 'amount': 5200},
                ]
            )

            response = self.app.get(
                '/income-statements/2016-09-01-to-2016-09-10.json'
            )
            self.assertEqual(200, response.status_code)
            self.assertJson(
                {
                    'start_date': '01.09.2016',
                    'end_date': '10.09.2016',
                    'net_income': 0,
                    'revenue': [
                        {
                            'code': '401',
                            'name': 'Revenue',
                            'type': 'revenue',
                            'balance': 0
                        }
                    ],
                    'expense': [
                        {
                            'code': '501',
                            'name': 'Expense',
                            'type': 'expense',
                            'balance': 0
                        }
                    ]
                },
                response
            )

            response = self.app.get(
                '/income-statements/2016-09-01-to-2016-09-11.json'
            )
            self.assertEqual(200, response.status_code)
            self.assertJson(
                {
                    'start_date': '01.09.2016',
                    'end_date': '11.09.2016',
                    'net_income': 4600,
                    'revenue': [
                        {
                            'code': '401',
                            'name': 'Revenue',
                            'type': 'revenue',
                            'balance': 5000
                        }
                    ],
                    'expense': [
                        {
                            'code': '501',
                            'name': 'Expense',
                            'type': 'expense',
                            'balance': 400
                        }
                    ]
                },
                response
            )

            response = self.app.get(
                '/income-statements/2016-09-01-to-2016-09-12.json'
            )
            self.assertEqual(200, response.status_code)
            self.assertJson(
                {
                    'start_date': '01.09.2016',
                    'end_date': '12.09.2016',
                    'net_loss': 600,
                    'revenue': [
                        {
                            'code': '401',
                            'name': 'Revenue',
                            'type': 'revenue',
                            'balance': 5000
                        }
                    ],
                    'expense': [
                        {
                            'code': '501',
                            'name': 'Expense',
                            'type': 'expense',
                            'balance': 5600
                        }
                    ]
                },
                response
            )

    def _create_account(self, code, name, type, app=None):
        payload = {'code': code, 'name': name, 'type': type}
        payload = {key: value
                   for key, value in payload.iteritems()
                   if value is not None}
        return self._post_json('/accounts', payload, app=app)

    def _get_account(self, code):
        return self.app.get('/accounts/{}'.format(code))

    def _record_transaction(self, date, description, items):
        return self._post_json('/transactions', {'date': date,
                                                 'description': description,
                                                 'items': items})

    def _get_transaction(self, tx_id):
        return self.app.get('/transactions/{}'.format(tx_id))

    def _post_json(self, url, data, app=None):
        if app is None:
            app = self.app
        return app.post(url, content_type='application/json',
                        data=json.dumps(data))

    def assertJson(self, expected_json, response):
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(expected_json, json.loads(response.data))


class MonetizeTestCase(unittest.TestCase):
    def test_monetize(self):
        self.assertEquals('0.00', webapp.monetize(0))
        self.assertEquals('0.01', webapp.monetize(1))
        self.assertEquals('1.00', webapp.monetize(100))
        self.assertEquals('1,234.00', webapp.monetize(123400))
        self.assertEquals('-1,000.00', webapp.monetize(-100000))


if __name__ == '__main__':
    unittest.main()
