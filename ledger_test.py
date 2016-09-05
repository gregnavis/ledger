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

    def _create_account(self, code, name):
        response = self.app.post('/accounts', content_type='application/json',
                                 data=json.dumps({'code': code, 'name': name}))
        self.assertEqual(200, response.status_code)

    def _get_account(self, code):
        response = self.app.get('/accounts/{}'.format(code))
        self.assertEqual(200, response.status_code)
        self.assertEqual('application/json', response.content_type)
        return json.loads(response.data)


if __name__ == '__main__':
    unittest.main()
