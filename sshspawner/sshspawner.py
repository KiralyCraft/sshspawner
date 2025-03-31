import asyncio, asyncssh
import os
from textwrap import dedent
import warnings
import random
import pwd
import shutil
from tempfile import TemporaryDirectory
import hashlib

from traitlets import Bool, Unicode, Integer, List, observe, default
from jupyterhub.spawner import Spawner


class SSHSpawner(Spawner):

    remote_hosts = List(trait=Unicode(),
            help="Possible remote hosts from which to choose remote_host.",
            config=True)

    remote_host = Unicode("remote_host",
            help="SSH remote host to spawn sessions on")

    remote_ip = Unicode("remote_ip",
            help="IP on remote side")

    remote_port = Unicode("22",
            help="SSH remote port number",
            config=True)

    ssh_command = Unicode("/usr/bin/ssh",
            help="Actual SSH command",
            config=True)

    path = Unicode("/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin",
            help="Default PATH (should include jupyter and python)",
            config=True)

    remote_port_command = Unicode("/usr/bin/python /usr/local/bin/get_port.py",
            help="Command to return unused port on remote host",
            config=True)
    hub_api_url = Unicode("",
            help=dedent("""If set, Spawner will configure the containers to use
            the specified URL to connect the hub api. This is useful when the
            hub_api is bound to listen on all ports or is running inside of a
            container."""),
            config=True)

    ssh_keyfile = Unicode("~/.ssh/id_rsa",
            help=dedent("""Key file used to authenticate hub with remote host.
            `~` will be expanded to the user's home directory and `{username}`
            will be expanded to the user's username"""),
            config=True)

    pid = Integer(0,
            help=dedent("""Process ID of single-user server process spawned for
            current user."""))

    resource_path = Unicode(".jupyterhub-resources",
            help=dedent("""The base path where all necessary resources are
            placed. Generally left relative so that resources are placed into
            this base directory in the user's home directory."""),
            config=True)

    # Load spawner state from a saved state dictionary.
    def load_state(self, state):
        super().load_state(state)
        if "pid" in state:
            self.pid = state["pid"]
        if "remote_ip" in state:
            self.remote_ip = state["remote_ip"]

    # Retrieve the current state of the spawner as a dictionary.
    def get_state(self):
        state = super().get_state()
        if self.pid:
            state["pid"] = self.pid
        if self.remote_ip:
            state["remote_ip"] = self.remote_ip
        return state

    # Clear the spawner state, resetting remote IP and PID.
    def clear_state(self):
        super().clear_state()
        self.remote_ip = "remote_ip"
        self.pid = 0

    # Start the notebook server on a remote host.
    async def start(self):
        username = self.user.name
        # Use the key file path directly (no certificate)
        kf = self.ssh_keyfile.format(username=username)
        
        self.remote_host = self.choose_remote_host()
        
        # Get a random unused port on the remote host
        self.remote_ip, remote_port = await self.remote_random_port()
        if self.remote_ip is None or remote_port is None or remote_port == 0:
            return False
        self.remote_port = str(remote_port)
        cmd = []
        cmd.extend(self.cmd)
        cmd.extend(self.get_args())    

        # Update the hub API URL if it has been specified
        if self.hub_api_url != "":
            old = "--hub-api-url={}".format(self.hub.api_url)
            new = "--hub-api-url={}".format(self.hub_api_url)
            for index, value in enumerate(cmd):
                if value == old:
                    cmd[index] = new
        
        # Append notebook configuration arguments
        cmd.append("--config=~/.jupyter/jupyter_notebook_config.py")
        cmd.append("--ip 0.0.0.0")
        cmd.append(f"--port={remote_port}")

        remote_cmd = ' '.join(cmd)
        self.log.info("Remote cmd:" + remote_cmd)
        self.log.info("Local cmd:" + str(self.cmd))
        # Execute the notebook command remotely and store the process ID
        self.pid = await self.exec_notebook(remote_cmd)
        self.log.info("Starting User: {}, PID: {}".format(self.user.name, self.pid))
        if self.pid < 0:
            return None
        return (self.remote_ip, remote_port)

    # Poll the remote process to check if it is still running.
    async def poll(self):
        if not self.pid:
            self.clear_state()
            return 0

        # Send signal 0 to check if process is alive
        alive = await self.remote_signal(0)
        self.log.debug("Polling returned {}".format(alive))
        if not alive:
            self.clear_state()
            return 0
        else:
            return None

    # Stop the remote notebook process.
    async def stop(self, now=False):
        # Send termination signal (SIGTERM)
        await self.remote_signal(15)
        self.clear_state()

    # Generate a remote username by computing the MD5 hash of the given username.
    def get_remote_user(self, username):
        return hashlib.md5(username.encode('utf-8')).hexdigest()

    # Randomly choose a remote host from the list of possible hosts.
    def choose_remote_host(self):
        return random.choice(self.remote_hosts)

    # Log any changes made to the remote_host attribute.
    @observe('remote_host')
    def _log_remote_host(self, change):
        self.log.debug("Remote host was set to %s." % self.remote_host)

    # Log any changes made to the remote_ip attribute.
    @observe('remote_ip')
    def _log_remote_ip(self, change):
        self.log.debug("Remote IP was set to %s." % self.remote_ip)

    # Connect to the remote host and obtain an unused random port.
    async def remote_random_port(self):
        username = self.get_remote_user(self.user.name)
        kf = self.ssh_keyfile.format(username=username)
        async with asyncssh.connect(self.remote_host, username=username, client_keys=[kf], known_hosts=None) as conn:
            result = await conn.run(self.remote_port_command)
            stdout = result.stdout
            stderr = result.stderr
            retcode = result.exit_status
        if stdout != b"":
            ip, port = stdout.split()
            port = int(port)
            self.port = port
            self.log.debug("ip={} port={}".format(ip, port))
        else:
            ip, port = None, None
            self.log.error("Failed to get a remote port")
            self.log.error("STDERR={}".format(stderr))
            self.log.debug("EXITSTATUS={}".format(retcode))
        return (ip, port)

    # Execute the notebook startup command on the remote host via SSH.
    async def exec_notebook(self, command):
        # Get environment for the spawned Jupyter server
        environment = super(SSHSpawner, self).get_env()
        environment['JUPYTERHUB_API_URL'] = self.hub_api_url
        
        if self.path:
            environment['PATH'] = self.path

        username = self.get_remote_user(self.user.name)


        ssh_key_path = self.ssh_keyfile.format(username=username)

        # Build the bash script that will run on the remote server
        bash_script_lines = ["#!/bin/bash"]
        for key, value in environment.items():
            bash_script_lines.append(f"export {key}='{value}'")

        bash_script_lines += [
            "unset XDG_RUNTIME_DIR",
            "touch .jupyter.log",
            "chmod 600 .jupyter.log",
            "run=true source initialSetup.sh >> .jupyter.log",
            f"{command} < /dev/null >> .jupyter.log 2>&1 & pid=$!",
            "echo $pid"
        ]

        bash_script_content = "\n".join(bash_script_lines)

        # Save script locally before sending it to the remote server
        local_script_path = f"/tmp/{self.user.name}_run.sh"
        with open(local_script_path, "w") as script_file:
            script_file.write(bash_script_content)

        if not os.path.isfile(local_script_path):
            raise Exception(f"The file {local_script_path} was not created.")
        else:
            with open(local_script_path, "r") as script_file:
                self.log.info(f"{local_script_path} was written as:\n{script_file.read()}")

        # Run the script remotely via SSH
        async with asyncssh.connect(
            self.remote_ip,
            username=username,
            client_keys=[ssh_key_path],
            known_hosts=None
        ) as conn:
            result = await conn.run("bash -s", stdin=local_script_path)

        stdout = result.stdout
        stderr = result.stderr
        return_code = result.exit_status

        self.log.info(f"exec_notebook status={return_code}")

        if stdout:
            return int(stdout.strip())
        else:
            return -1

    # Send a signal to the remote process via SSH.
    async def remote_signal(self, sig):
        username = self.get_remote_user(self.user.name)
        kf = self.ssh_keyfile.format(username=username)
        command = "kill -s %s %d < /dev/null" % (sig, self.pid)
        async with asyncssh.connect(self.remote_ip, username=username,
                                    client_keys=[kf], known_hosts=None) as conn:
            result = await conn.run(command)
            stdout = result.stdout
            stderr = result.stderr
            retcode = result.exit_status
        self.log.debug("command: {} returned {} --- {} --- {}".format(command, stdout, stderr, retcode))
        return (retcode == 0)

    # Stage certificate files by moving and copying key and CA files.
    def stage_certs(self, paths, dest):
        # Certificate staging is now simplified since SSH certificates are not used.
        shutil.move(paths['keyfile'], dest)
        shutil.copy(paths['cafile'], dest)

        key_base_name = os.path.basename(paths['keyfile'])
        ca_base_name = os.path.basename(paths['cafile'])
        key = os.path.join(self.resource_path, key_base_name)
        ca = os.path.join(self.resource_path, ca_base_name)
        return {
            "keyfile": key,
            "cafile": ca,
        }
