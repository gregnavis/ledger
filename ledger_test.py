import json
import unittest

import ledger


class LedgerTestCase(unittest.TestCase):
    def setUp(self):
        ledger.app.config['TESTING'] = True
        self.app = ledger.app.test_client()

    def tearDown(self):
        ledger.database.reset()

    def test_create_account(self):
        self.assertEqual(
            201,
            self._create_account('101', 'Cash', 'asset').status_code
        )

        response = self._get_account('101')
        self.assertEqual(200, response.status_code)
        self.assertEqual('application/json', response.content_type)
        self.assertJson(
            {'name': 'Cash', 'code': '101', 'type': 'asset', 'balance': 0},
            response
        )

    def test_create_account_types(self):
        self.assertEqual(
            201,
            self._create_account('101', 'Cash', 'asset').status_code
        )
        self.assertEqual(
            201,
            self._create_account('201', 'Bank Loan', 'liability').status_code
        )
        self.assertEqual(
            201,
            self._create_account('301', 'Share Capital', 'equity').status_code
        )
        self.assertEqual(
            201,
            self._create_account('401', 'Revenue', 'revenue').status_code
        )
        self.assertEqual(
            201,
            self._create_account('501', 'Expense', 'expense').status_code
        )

    def test_create_account_twice(self):
        self._create_account('101', 'Cash', 'asset')
        self.assertEqual(
            409,
            self._create_account('101', 'Cash', 'asset').status_code
        )

    def test_incomplete_create_account(self):
        self.assertEqual(
            400,
            self._post_json('/accounts',
                            {'code': '101', 'type': 'asset'}).status_code
        )
        self.assertEqual(
            400,
            self._post_json('/accounts',
                            {'name': 'Cash', 'type': 'asset'}).status_code
        )
        self.assertEqual(
            400,
            self._post_json('/accounts',
                            {'code': '101', 'name': 'Cash'}).status_code
        )

    def test_create_account_with_invalid_type(self):
        response = self._create_account('101', 'Cash', 'other')
        self.assertEqual(400, response.status_code)

    def test_create_account_without_json(self):
        response = self.app.post('/accounts',
                                 data={'code': '101', 'name': 'Cash'})
        self.assertEqual(400, response.status_code)

    def test_get_non_existent_account(self):
        response = self._get_account('101')
        self.assertEqual(404, response.status_code)

    def test_record_transaction(self):
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

        self.assertEqual(10000,
                         json.loads(self._get_account('101').data)['balance'])
        self.assertEqual(-10000,
                         json.loads(self._get_account('320').data)['balance'])

    def test_record_empty_transaction(self):
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

    def test_record_transaction_with_invalid_date(self):
        self._create_account('101', 'Cash', 'asset')
        self._create_account('320', 'Share Capital', 'equity')

        response = self._record_transaction(
            '20160901',
            "Record the founder's investment",
            [
                {'account_code': '101', 'amount': 10000},
                {'account_code': '320', 'amount': -10000}
            ]
        )
        self.assertEqual(400, response.status_code)

    def test_get_transaction(self):
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

        transaction_id = int(response.data)

        response = self.app.get('/transactions/{}'.format(transaction_id))
        self.assertEqual(200, response.status_code)
        self.assertJson({
            'date': '2016-09-01',
            'description': "Record the founder's investment",
            'items': [
                {'account_code': '101', 'amount': 10000},
                {'account_code': '320', 'amount': -10000}
            ]},
            response
        )

    def test_get_transactions(self):
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
        self._create_account('101', 'Cash', 'asset')
        self._create_account('102', 'Equipment', 'asset')
        self._create_account('201', 'Bank Loan', 'liability')
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

    def _create_account(self, code, name, type):
        return self._post_json('/accounts', {'code': code, 'name': name,
                                             'type': type})

    def _get_account(self, code):
        return self.app.get('/accounts/{}'.format(code))

    def _record_transaction(self, date, description, items):
        return self._post_json('/transactions', {'date': date,
                                                 'description': description,
                                                 'items': items})

    def _post_json(self, url, data):
        return self.app.post(url, content_type='application/json',
                             data=json.dumps(data))

    def assertJson(self, expected_json, response):
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(expected_json, json.loads(response.data))


class MonetizeTestCase(unittest.TestCase):
    def test_monetize(self):
        self.assertEquals('0.00', ledger.monetize(0))
        self.assertEquals('0.01', ledger.monetize(1))
        self.assertEquals('1.00', ledger.monetize(100))
        self.assertEquals('1,234.00', ledger.monetize(123400))
        self.assertEquals('-1,000.00', ledger.monetize(-100000))


if __name__ == '__main__':
    unittest.main()
