all:
	pip uninstall sshspawner -y
	python3 setup.py install
	systemctl restart jupyterhub

