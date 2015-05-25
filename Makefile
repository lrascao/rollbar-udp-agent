
all: build

build:
	python setup.py build sdist

upload: build
	twine upload dist/*

clean:
	python setup.py clean

distclean: clean
	rm -rf build/ dist/ rollbar_udp_agent.egg-info/

