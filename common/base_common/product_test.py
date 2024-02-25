import re
import time

from common.base_common import com_util, ssh_shell


class ProductTest:
    def __init__(self, config):
        self.config = config
        self.emuSshSessions = None

    def regrep_soc_port(self, shell):
        info = shell.run('grep -rn "Guest port no: 22" demo/run_dir/xrun.log', mod='all')
        m = 'Host port no: (.*) '
        c = re.compile(m, 0)
        g = c.findall(info)
        if g is None or len(g) == 0:
            print('can not get soc port')
            return None
        print('all soc port:', g)
        curport = g[0]
        return curport

    def login_n2(self, shell):
        runpath = com_util.get_str(self.config.usr_config, 'runpath')
        shell.run(f'cd {runpath}')
        curport = self.regrep_soc_port(shell)
        if curport is None:
            return False
        ret = shell.run_by_auth_yes(f'ssh root@127.0.0.1 -p {curport}', 'root')
        return ret

    def login_soc_try(self, shell, timeout=60, timestep=30):
        param = {
            'remote_ip': '127.0.0.1',
            'remote_port': 6000,
            'user': 'root',
            'psword': 'jmnd',
            'header_list': ['dpu_debug-> ']
        }
        sshUsername = com_util.get_str(param, 'user')
        sshPassword = com_util.get_str(param, 'psword')
        sshServer = com_util.get_str(param, 'remote_ip')
        sshPort = com_util.get_int(param, 'remote_port', 22)
        header_list = com_util.get_list(param, 'header_list')
        shell.set_default_end_list(shell.default_end_list + header_list)

        index = 0
        while index < timeout:
            ret = shell.run_by_auth_yes(f'ssh {sshUsername}@{sshServer} -p {sshPort}', sshPassword)
            if ret:
                print('login soc proc suc')
                return ret
            time.sleep(timestep)        # 后端sleep时间
            index = index + 1
            print(f'try login soc proc again: {index}')
        print('login soc proc timeout')
        return False

    def login_host_server_try(self, shell, timeout=60, timestep=30):
        sshUsername = com_util.get_str(self.config.host_server_cfg, 'user')
        sshPassword = com_util.get_str(self.config.host_server_cfg, 'psword')
        sshServer = com_util.get_str(self.config.host_server_cfg, 'remote_ip')
        sshPort = com_util.get_int(self.config.host_server_cfg, 'remote_port', 22)

        index = 0
        while index < timeout:
            ret = shell.run_by_auth_yes(f'ssh {sshUsername}@{sshServer} -p {sshPort}', sshPassword)
            if ret:
                print('login host suc')
                return True
            time.sleep(timestep)  # 后端sleep时间
            index = index + 1
            print(f'try login host again: {index}')
        print('login host timeout')
        return False

    def login_host_try(self, shell, timeout=60, timestep=30):
        param = {
            'remote_ip': '127.0.0.1',
            'remote_port': 6000,
            'user': 'root',
            'psword': 'jmnd',
            'header_list': ['dpu_debug-> ']
        }

        sshUsername = com_util.get_str(param, 'user')
        sshPassword = com_util.get_str(param, 'psword')
        sshServer = com_util.get_str(param, 'remote_ip')
        sshPort = com_util.get_int(param, 'remote_port', 22)
        header_list = com_util.get_list(param, 'header_list')
        shell.set_default_end_list(shell.default_end_list + header_list)

        index = 0
        while index < timeout:
            ret = shell.run_by_auth_yes(f'ssh {sshUsername}@{sshServer} -p {sshPort}', sshPassword)
            if ret:
                print('login host proc suc')
                return True
            time.sleep(timestep)
            index = index + 1
            print(f'try login host proc again: {index}')
        print('login host proc timeout')
        return False

    def logout_n2(self, shell):
        shell.run('\x04')

    def logout_soc(self, shell):
        shell.run('\x04')

    def logout_host(self, shell):
        shell.run('\x04')

    def logout_host_server(self, shell):
        shell.run('\x04')

    def login_emu(self):
        if self.emuSshSessions is not None:
            return True

        self.emuSshSessions = ssh_shell.connect_ssh_session(self.config.emu_cfg)  # 从etx连接emu
        if self.emuSshSessions is None:
            return False
        return True

    def __del__(self):
        print('del product_test obj')
