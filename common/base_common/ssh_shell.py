import time

from common.base_common import com_util
from common.base_common import ssh_run


def connect_ssh_session(ssh_info):
    sshUsername = com_util.get_str(ssh_info, 'user')
    sshPassword = com_util.get_str(ssh_info, 'psword')
    sshServer = com_util.get_str(ssh_info, 'remote_ip')
    sshPort = com_util.get_int(ssh_info, 'remote_port', 22)

    try:
        sshSessions = ssh_run.SSHSessions(sshServer, sshUsername, sshPassword, port=sshPort)
        if sshSessions.connect() != 0:
            return None
    except BaseException as e:
        print(e)
        return None
    return sshSessions


def connect_ssh_session_try(ssh_cfg, timeout=60, timestep=30):
    index = 0
    while index < timeout:
        sshSessions = connect_ssh_session(ssh_cfg)
        if sshSessions is None:
            time.sleep(timestep)
        else:
            return sshSessions
        index = index + 1
    print('connect session timeout')
    return None


def connect_ssh(ssh_info):
    sshUsername = com_util.get_str(ssh_info, 'user')
    sshPassword = com_util.get_str(ssh_info, 'psword')
    sshServer = com_util.get_str(ssh_info, 'remote_ip')
    sshPort = com_util.get_int(ssh_info, 'remote_port', 22)
    headerList = com_util.get_list(ssh_info, 'header_list')

    try:
        sshSessions = ssh_run.SSHSessions(sshServer, sshUsername, sshPassword, port=sshPort)
        if sshSessions.connect() != 0:
            return None, None
    except BaseException as e:
        print(e)
        return None, None

    print(sshServer)
    if len(headerList) > 0:
        shell = sshSessions.open_shell(rcv_end_list=headerList)
        shell.set_default_end_list(headerList)
    else:
        shell = sshSessions.open_shell()
    if shell is None:
        sshSessions.close()
        sshSessions = None
    return shell, sshSessions


def connect_ssh_try(ssh_info):
    sshServer = com_util.get_str(ssh_info, 'remote_ip')
    sshPort = com_util.get_int(ssh_info, 'remote_port', 22)
    timeout = 60
    while True:
        ssh_shell, ssh_session = connect_ssh(ssh_info)
        if ssh_shell is not None:
            return ssh_shell, ssh_session
        timeout = timeout - 1
        if timeout <= 0:
            break
        print(f'waiting {sshServer}:{sshPort}')
        time.sleep(5)
    print(f'waiting {sshServer}:{sshPort} timeout')


if __name__ == '__main__':
    param = {
        'remote_ip': '10.20.70.22',
        'remote_port': 6000,
        'user': 'root',
        'psword': 'jmnd',
        'header_list': ['jmnd_shell >> ']
    }
    shell, session = connect_ssh(param)
    shell.run('help')
    shell.close()
    session.close()
