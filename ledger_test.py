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

    def _create_account(self, code, name, type):
        return self._post_json('/accounts', {'code': code, 'name': name,
                                             'type': type})

    def _get_account(self, code):
        return self.app.get('/accounts/{}'.format(code))

    def _post_json(self, url, data):
        return self.app.post(url, content_type='application/json',
                             data=json.dumps(data))

    def assertJson(self, expected_json, response):
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(expected_json, json.loads(response.data))


if __name__ == '__main__':
    unittest.main()
