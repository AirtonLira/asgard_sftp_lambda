build:
	virtualenv -p /usr/bin/python3.8 asgard
	source asgard/bin/activate
	pip freeze > requirements.txt
	pip install -r requirements.txt -t .
	zip -r package.zip asgard/pipp