from tests.pytestCase.Common.Object.ConfPage import SIMConfPage, EMUConfPage, HYBRIDConfPage,CRBConfPage
import logging
from common.ssh_run import SSHSessions

"""
relative_path
"""
SIM_NetBlk_Legacy_ConfPath = '/config/SIM-NetBlk-Legacy.conf'
SIM_NetBlk_Modern_ConfPath = '/config/SIM-NetBlk-Modern.conf'
SIM_NVMe_ConfPath = '/config/SIM-Nvme.conf'

class ItSession(object):
    env_type: str
    dev_type: str

    def __init__(self, env_type, dev_type):
        self.env_type = env_type
        self.dev_type = dev_type
        self._configure = None
        self._n2_session = None
        self._host_session = None

    def __del__(self):
        self.close()

    def close(self):
        # 关闭 _n2_session
        if self._n2_session is not None:
            self._n2_session.close()
            self._n2_session = None
            logging.info(f"_n2_session close.")
        # 关闭 _host_session
        if self._host_session is not None:
            self._host_session.close()
            self._host_session = None
            logging.info(f"_host_session close.")

    def login_n2(self):
        N2Server = self._configure.get_n2_server()
        N2_SSHSession = SSHSessions(N2Server.hostname, N2Server.username,
                                    N2Server.password, N2Server.port)
        ret = N2_SSHSession.connect()
        logging.info(f"N2_SSHSession.connect ret={ret}")
        assert ret == 0
        return N2_SSHSession

    def login_host(self):
        hostServer = self._configure.get_host_server()
        host_SSHSession = SSHSessions(hostServer.hostname, hostServer.username,
                                      hostServer.password, hostServer.port)
        assert host_SSHSession.connect() == 0
        return host_SSHSession

    def get_configure(self):
        return self._configure

    def get_n2_session(self):
        return self._n2_session

    def get_host_session(self):
        return self._host_session


class SimSession(ItSession):
    def __init__(self, env_type, sim_type):
        super().__init__(env_type, sim_type)
        self._configure = SIMConfPage(env_type, sim_type)
        self._n2_session = self.login_n2()
        self._host_session = self.login_host()


    def _login_second_host(self):
        second_host_server = self._configure.get_second_host_server()
        second_host_SSHSession = SSHSessions(second_host_server.hostname, second_host_server.username,
                                             second_host_server.password, second_host_server.port)
        assert second_host_SSHSession.connect() == 0
        return second_host_SSHSession

    def get_second_host_session(self):
        if self._second_host_session is None:
            self._second_host_session = self._login_second_host()
        return self._second_host_session

    def __del__(self):
        self.close()

    def close(self):
        # 关闭 _n2_session
        super(SimSession, self).close()

class EMUSession(ItSession):
    def __init__(self, env_type, dev_type):
        super().__init__(env_type, dev_type)
        self._configure = EMUConfPage(env_type, dev_type)
        self._n2_session = self.login_n2()
        self._host_session = self.login_host()
        # EMU 环境特有
        self._bmc_session = None


class HybridSession(ItSession):
    def __init__(self, env_type, dev_type):
        super().__init__(env_type, dev_type)
        self._configure = HYBRIDConfPage(env_type, dev_type)
        self._n2_session = self.login_n2()
        self._host_session = self.login_host()
        self._bmc_session = None


class ItSessionFactory:
    @staticmethod
    def create_itSession(env_type, dev_type):
        """
        功能：测试慢速路径流通(host-uplink)。

        参数：
        env_type: IT会话对象，集成测试会话。
        dev_type: 前端设备类型，‘net|blk|nvme’的其中一种。
        dev_queue_type:  后端队列类型，'Legacy|Modern|Packed'的其中一种。

        返回：
        函数没有明确返回值，但可能会通过it_session对设备进行配置。

        示例：
        调用 netpfdev_host_uplink_lsp(session, 'net', 'Legacy') 测试Legacy网络设备的HostToUplin慢速路径流通。
        """
        if env_type == "EMU":
            return EMUSession(env_type, dev_type)
        elif env_type == "SIM":
            return SimSession(env_type, dev_type)
        elif env_type == "HYBRID":
            return HybridSession(env_type, dev_type)
        elif env_type == "CRB":
            return HybridSession(env_type, dev_type)
        else:
            raise ValueError(f"Invalid environment type.env_type:{env_type},dev_type:{dev_type}")


def main():
    itSession = ItSessionFactory.create_itSession("SIM", "LEGACY")
    print(itSession.get_configure())


if __name__ == "__main__":
    main()
