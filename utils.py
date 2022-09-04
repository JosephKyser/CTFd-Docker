from CTFd.utils import cache
from CTFd.utils.decorators import admins_only
from CTFd.utils.user import is_admin
from CTFd.models import db
from .models import Containers

import json
import subprocess
import socket
import tempfile
import shutil
import logging
import re
import sys
import os
logger = logging.getLogger(__name__)


@cache.memoize()
def can_create_container():
    try:
        subprocess.check_output(['docker', 'version'])
        return True
    except (subprocess.CalledProcessError, OSError):
        return False


def import_image(name):
    try:
        info = json.loads(subprocess.check_output(['docker', 'inspect', '--type=image', name]))
        container = Containers(name=name, buildfile=None)
        db.session.add(container)
        db.session.commit()
        db.session.close()
        return True
    except subprocess.CalledProcessError:
        return False


def create_image(name, buildfile, files):
    print(f"{buildfile}", file=sys.stderr)
    if not can_create_container():
        print('can_create_container failed')
        return False
    folder = tempfile.mkdtemp(prefix='ctfd')
    tmpfile = tempfile.NamedTemporaryFile(dir=folder, mode='w', delete=False)
    logger.error(tmpfile)

    
    tmpfile.write(buildfile.read().decode())
    tmpfile.close()

    for f in files:
        if f.filename.strip():
            filename = os.path.basename(f.filename)
            f.save(os.path.join(folder, filename))
    # repository name component must match "[a-z0-9](?:-*[a-z0-9])*(?:[._][a-z0-9](?:-*[a-z0-9])*)*"
    # docker build -f tmpfile.name -t name
    try:
        cmd = ['docker', 'build', '-f', tmpfile.name, '-t', name, folder]
        print(cmd)
        subprocess.call(cmd)
        container = Containers(name, buildfile)
        db.session.add(container)
        db.session.commit()
        db.session.close()
        # shutil.rmtree(folder)
        return True
    except subprocess.CalledProcessError:
        return False


def is_port_free(port):
    s = socket.socket()
    result = s.connect_ex(('127.0.0.1', port))
    if result == 0:
        s.close()
        return False
    return True


def delete_image(name):
    try:
        subprocess.call(['docker', 'rm', name])
        subprocess.call(['docker', 'rmi', name])
        return True
    except subprocess.CalledProcessError:
        return False


def run_image(name):
    try:
        info = json.loads(subprocess.check_output(['docker', 'inspect', '--type=image', name]))

        try:
            ports_asked = info[0]['Config']['ExposedPorts'].keys()
            ports_asked = [int(re.sub('[A-Za-z/]+', '', port)) for port in ports_asked]
        except KeyError:
            ports_asked = []

        cmd = ['docker', 'run', '-itd']
        ports_used = []
        for port in ports_asked:
            if is_port_free(port):
                cmd.append('-p')
                cmd.append('{}:{}'.format(port, port))
            else:
                cmd.append('-p')
                ports_used.append('{}'.format(port))
        cmd += ['--name', name, name]
        print(cmd)
        subprocess.call(cmd)
        return True
    except subprocess.CalledProcessError:
        return False


def container_start(name):
    try:
        cmd = ['docker', 'start', name]
        print(cmd)
        subprocess.call(cmd)
        return True
    except subprocess.CalledProcessError:
        return False


def container_stop(name):
    try:
        cmd = ['docker', 'stop', name]
        print(cmd)
        subprocess.call(cmd)
        return True
    except subprocess.CalledProcessError:
        return False


def container_status(name):
    try:
        data = json.loads(subprocess.check_output(['docker', 'inspect', '--type=container', name]))
        status = data[0]["State"]["Status"]
        return status
    except subprocess.CalledProcessError:
        return 'missing'



def container_ports(name, verbose=False):
    try:
        info = json.loads(subprocess.check_output(['docker', 'inspect', '--type=container', name]))
        print(name, info)
        if verbose:
            ports = info[0]["NetworkSettings"]["Ports"]
            if not ports:
                return []
            final = []
            print(ports)
            for port in ports.keys():
                if ports[port] is not None and ports[port][0] is not None and ports[port][0]["HostPort"] is not None:
                    final.append("".join([ports[port][0]["HostPort"], '->', port]))
            return final
        else:
            ports = info[0]['Config']['ExposedPorts'].keys()
            if not ports:
                return []
            ports = [int(re.sub('[A-Za-z/]+', '', port)) for port in ports]
            return ports
    except subprocess.CalledProcessError:
        return []