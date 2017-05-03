
release:
	@echo "Removing dist/ directory ..."
	@rm -rf dist/
	@echo "Creating Python source distribution ..."
	@python setup.py sdist
	@echo "Uploading distribution to PyPI ..."
	@twine upload dist/*.zip
