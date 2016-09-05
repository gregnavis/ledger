from flask import Flask, jsonify, request

app = Flask(__name__)


class Database(object):
    def __init__(self):
        self.accounts = []

    def create_account(self, code, name):
        '''Create an account with a given code and name.'''
        code = str(code)
        name = str(name)

        if self.get_account(code):
            return RuntimeError('The account {} already exists'.format(code))

        self.accounts.append({'code': code, 'name': name, 'balance': 0})

    def get_account(self, code):
        '''Return the account identified by the specified code.'''
        code = str(code)

        for account in self.accounts:
            if code == account['code']:
                return account
        else:
            return None


database = Database()


@app.route('/accounts/<code>', methods=['GET'])
def get_account(code):
    return jsonify(database.get_account(code))


@app.route('/accounts', methods=['POST'])
def create_account():
    database.create_account(request.json['code'], request.json['name'])
    return 'Created'


if __name__ == '__main__':
    app.run()
