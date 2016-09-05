.DEFAULT: test

.PHONY: precommit
precommit: pep8 test

.PHONY: pep8
pep8:
	pep8 --max-line-length=80 ledger.py ledger_test.py

.PHONY: test
test:
	python ledger_test.py

.PHONY: setup
setup:
	ln -sf ../../precommit ./.git/hooks/pre-commit
