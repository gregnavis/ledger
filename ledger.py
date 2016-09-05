from flask import Flask, jsonify, request

app = Flask(__name__)


class Database(object):
    def __init__(self):
        self.reset()

    def reset(self):
        '''Reset the database (for testing purposes).'''
        self.accounts = []

    def create_account(self, code, name):
        '''Create an account with a given code and name.'''
        code = str(code)
        name = str(name)

        if self.get_account(code):
            return False

        self.accounts.append({'code': code, 'name': name, 'balance': 0})
        return True

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
    if 'name' not in request.json:
        return 'Missing "name"', 400
    if 'code' not in request.json:
        return 'Missing "code"', 400
    if database.create_account(request.json['code'], request.json['name']):
        return 'Created'
    else:
        return 'Account "{}" already exists'.format(request.json['code']), 409


if __name__ == '__main__':
    app.run()
