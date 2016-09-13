URL=http://127.0.0.1:5000

.DEFAULT: test

.PHONY: precommit
precommit: pep8 test

.PHONY: pep8
pep8:
	pep8 --max-line-length=80 ledger.py webapp.py webapp_test.py

.PHONY: test
test:
	python webapp_test.py
	python ledger_test.py

.PHONY: setup
setup:
	ln -sf ../../precommit ./.git/hooks/pre-commit

.PHONY: seed
seed:
	curl -fS -H "Content-Type: application/json" -X POST -d '{"name":"Cash","code":"101","type":"asset"}' "${URL}/accounts"
	curl -fS -H "Content-Type: application/json" -X POST -d '{"name":"Equipment","code":"102","type":"asset"}' "${URL}/accounts"
	curl -fS -H "Content-Type: application/json" -X POST -d '{"name":"Bank Loan","code":"201","type":"liability"}' "${URL}/accounts"
	curl -fS -H "Content-Type: application/json" -X POST -d '{"name":"Share Capital","code":"301","type":"equity"}' "${URL}/accounts"
	curl -fS -H "Content-Type: application/json" -X POST -d '{"name":"Consulting Revenue","code":"401","type":"revenue"}' "${URL}/accounts"
	curl -fS -H "Content-Type: application/json" -X POST -d '{"name":"Business Travel","code":"501","type":"expense"}' "${URL}/accounts"
	curl -fS -H "Content-Type: application/json" -X POST -d '{"date":"2016-09-01","description":"Record the initial investment","items":[{"account_code":"101","amount":100000},{"account_code":"301","amount":-100000}]}' "${URL}/transactions"
	curl -fS -H "Content-Type: application/json" -X POST -d '{"date":"2016-09-03","description":"Buy a computer","items":[{"account_code":"101","amount":-50000},{"account_code":"102","amount":200000},{"account_code":"201","amount":-150000}]}' "${URL}/transactions"
	curl -fS -H "Content-Type: application/json" -X POST -d '{"date":"2016-09-04","description":"Software consulting for Acme Inc.","items":[{"account_code":"101","amount":50000},{"account_code":"401","amount":-50000}]}' "${URL}/transactions"
	curl -fS -H "Content-Type: application/json" -X POST -d '{"date":"2016-09-04","description":"On-site visit to Acme Inc.","items":[{"account_code":"101","amount":-4500},{"account_code":"501","amount":4500}]}' "${URL}/transactions"
