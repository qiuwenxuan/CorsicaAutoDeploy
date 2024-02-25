import time
from comm import product_test


class PtestShell(product_test.ProductTest):
    def __init__(self, config):
        product_test.ProductTest.__init__(self, config)

    def open_emu_shell(self):
        assert self.login_emu()
        cur_shell = self.emuSshSessions.open_shell()
        assert cur_shell is not None
        return cur_shell

    def open_n2_shell(self):
        cur_shell = self.open_emu_shell()
        assert self.login_n2(cur_shell)
        return cur_shell

    def close_n2_shell(self, shell):
        self.logout_n2(shell)

    def open_soc_shell(self):
        cur_shell = self.open_n2_shell()
        assert self.login_soc_try(cur_shell)  # 从n2登录到后端进程的6000号端口, 多次尝试
        cur_shell.run('')
        time.sleep(0.5)
        cur_shell.run('enable')
        time.sleep(0.5)
        cur_shell.run('')
        return cur_shell

    def close_soc_shell(self, shell):
        shell.run('')
        shell.run('disable')
        shell.run('')
        self.logout_soc(shell)
        self.logout_n2(shell)

    def open_host_server_shell(self):
        cur_shell = self.open_emu_shell()
        assert self.login_host_server_try(cur_shell)
        return cur_shell

    def close_host_server_shell(self, shell):
        self.logout_host_server(shell)

    def open_host_shell(self):
        cur_shell = self.open_host_server_shell()
        assert self.login_host_try(cur_shell)
        cur_shell.run('')
        time.sleep(0.5)
        cur_shell.run('enable')
        time.sleep(0.5)
        cur_shell.run('')
        return cur_shell

    def close_host_shell(self, shell):
        shell.run('')
        shell.run('disable')
        shell.run('')
        self.logout_host(shell)
        self.logout_host_server(shell)
