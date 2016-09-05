import json
import unittest

import ledger


class LedgerTestCase(unittest.TestCase):
    def setUp(self):
        ledger.app.config['TESTING'] = True
        self.app = ledger.app.test_client()

    def test_create_account(self):
        self._create_account('101', 'Cash')
        self.assertEqual(
            {'name': 'Cash', 'code': '101', 'balance': 0},
            self._get_account('101')
        )

    def test_incomplete_create_account(self):
        self.assertEqual(
            400,
            self._post_json('/accounts', {'code': '101'}).status_code
        )
        self.assertEqual(
            400,
            self._post_json('/accounts', {'name': 'Cash'}).status_code
        )

    def _create_account(self, code, name):
        response = self._post_json('/accounts', {'code': code, 'name': name})
        self.assertEqual(200, response.status_code)

    def _get_account(self, code):
        response = self.app.get('/accounts/{}'.format(code))
        self.assertEqual(200, response.status_code)
        self.assertEqual('application/json', response.content_type)
        return json.loads(response.data)

    def _post_json(self, url, data):
        return self.app.post(url, content_type='application/json',
                             data=json.dumps(data))


if __name__ == '__main__':
    unittest.main()
