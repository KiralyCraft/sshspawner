
# sshspawner

The *sshspawner* enables JupyterHub to spawn single-user notebook servers on remote hosts over SSH.
We provide this package as a reference implementation only, the authors offer no general user support.

This fork has been updated to function without certificates, and instead only rely on keys. 

## Features

* Supports SSH key-based authentication
* Pool of remote hosts for spawning notebook servers
* Extensible custom load-balacing for remote host pool
* Remote-side scripting to return IP and port

## Requirements

* Python 3
* [JupyterHub](http://jupyter.org/install)
* [AsyncSSH](https://asyncssh.readthedocs.io/en/latest/#installation)

## Installation

```
python3 setup.py install
```

Install [scripts/get_port.py](scripts/get_port.py) on remote host and set correct path for `c.SSHSpawner.remote_port_command` in [jupyterhub_config.py](jupyterhub_config.py)
The script checks for a free TCP port which it returns to the hub, so that it launches the notebook on the correct port.  

The current design assumes:
- That the user running the JupyterHub has a `~/.ssh/id_rsa` which it can use to log in to any user on the remote servers.
- The host running the notebooks must have the `venv` system-wide module for Python3 installed, as well as `jupyterhub` (or whatever provides `jupyterhub-singleuser`)

The remote application launched is `jupyterhub-singleuser`. 

## Configuration

See [jupyterhub_config.py](jupyterhub_config.py) for a sample configuration.
Adjust values for your installation.

## License

All code is licensed under the terms of the revised BSD license.

## Resources

- [Documentation for JupyterHub](https://jupyterhub.readthedocs.io)
- [Documentation for Project Jupyter](https://jupyter.readthedocs.io/en/latest/index.html) | [PDF](https://media.readthedocs.org/pdf/jupyter/latest/jupyter.pdf)
- [Project Jupyter website](https://jupyter.org)

