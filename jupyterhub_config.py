c.JupyterHub.base_url = "/jhub/"
c.JupyterHub.redirect_to_server = False

# Sample ConfigurationS
c.JupyterHub.spawner_class = 'sshspawner.sshspawner.SSHSpawner'

# The remote host to spawn notebooks on
c.SSHSpawner.remote_hosts = ['CHANGE_ME']
c.SSHSpawner.remote_port = '22'
c.SSHSpawner.ssh_command = 'ssh'

# The system path for the remote SSH session. Must have the jupyter-singleuser and python executables
#c.SSHSpawner.path = '/global/common/cori/software/python/3.5-anaconda/bin:/global/common/cori/das/jupyterhub/:/usr/common/usg/bin:/usr/bin:/bin:/usr/bin/X11:/usr/games:/usr/lib/mit/bin:/usr/lib/mit/sbin'

# The command to return an unused port on the target system. See scripts/get_port.py for an example
c.SSHSpawner.remote_port_command = '/usr/bin/python /root/sshspawner/scripts/get_port.py -i'
c.SSHSpawner.hub_api_url = 'http://CHANGE_ME:15001/jhub/hub/api'
#c.Spawner.cmd = "python -m jupyter lab"
#c.Spawner.cmd = "jupyter-labhub"
c.Spawner.cmd = "jupyterhub-singleuser"
c.Spawner.ip = '0.0.0.0'

c.JupyterHub.hub_port = 15001
c.JupyterHub.hub_ip = '0.0.0.0'

# Astea is bune!!

c.Spawner.default_url = '/lab'
c.Spawner.notebook_dir = '/home/{username}'
