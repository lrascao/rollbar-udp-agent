
all: build

build:
	python setup.py build sdist

develop: build
	python setup.py develop

upload: build
	twine upload dist/*

clean:
	python setup.py clean

distclean: clean
	rm -rf build/ dist/ rollbar_udp_agent.egg-info/

