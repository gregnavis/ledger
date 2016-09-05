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


if __name__ == '__main__':
    unittest.main()
