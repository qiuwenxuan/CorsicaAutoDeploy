import configparser
import logging
import os

from common.Object.ItestObject import EnvironmentType, DevType, ItestObject
from common.utils.exception import ENVError, TYPEError

SIM_NetBlk_Legacy_ConfPath = '/config/SIM/SIM-NetBlk-Legacy.conf'
SIM_NetBlk_Modern_ConfPath = '/config/SIM/SIM-NetBlk-Modern.conf'
SIM_NVMe_ConfPath = '/config/SIM/SIM-Nvme.conf'
EMU_ConfPath = '/config/EMU/EMU.conf'
HYBRID_ConfPath = '/config/HYBRID/HYBRID.conf'
CRB_ConfPath = '/config/CRB/CRB.conf'


def read_conf(path):
    try:
        config_reader = ConfigReader(path)

        # 获取所有节（sections）
        sections = config_reader.get_all_sections()

        # 逐个打印配置项的值
        for section in sections:
            logging.info(f'[{section}]')
            options = config_reader.get_section_options(section)
            for option in options:
                value = config_reader.get_option_value(section, option)
                logging.info(f'{option} = {value}')
            logging.info(f' ')
        return config_reader
    except FileNotFoundError as e:
        logging.info(e)


def get_conf_abspath(conf_path):
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    conf_dir = f"{parent_dir}/../../"
    logging.info(f"Current parentdir:{parent_dir},Confdir:{conf_dir}")

    ConfAbsPath = f"{conf_dir}{conf_path}"
    logging.info(f"ConfAbsPath:{ConfAbsPath}")
    assert os.path.exists(ConfAbsPath)
    return ConfAbsPath


def parse_server(config_reader, server_type):
    """parse server.

        :param config_reader: 读取配置文件类
        :param server_type: N2 or host or host_2 or BMC
        """
    if server_type not in {'N2', 'host', 'host_2', 'BMC'}:
        raise TYPEError(f'server_type 类型错误：server_type={server_type}')
    else:
        server = Server(config_reader.get_option_value(f'{server_type}', 'hostname'),
                        config_reader.get_option_value(f'{server_type}', 'port'),
                        config_reader.get_option_value(f'{server_type}', 'username'),
                        config_reader.get_option_value(f'{server_type}', 'password'))
        return server


def set_itestObject(p_env_type, p_dev_type):
    """
       ItestObject(EnvironmentType:EMU,DevType:LEGACY or MODERN or NVME orPACKED )
       ItestObject(EnvironmentType:CRB,DevType:LEGACY or MODERN or NVME orPACKED )
       ItestObject(EnvironmentType:SIM,DevType:LEGACY or MODERN or NVME)
       ItestObject(EnvironmentType:HYBRID,DevType:LEGACY or MODERN or NVME orPACKED )
    """
    upper_env_type = p_env_type.upper()
    upper_dev_type = p_dev_type.upper()
    if upper_env_type in {"EMU", "HYBRID", "CRB"} and \
            upper_dev_type not in {DevType.LEGACY.name, DevType.MODERN.name, DevType.NVME.name, DevType.PACKED.name}:
        raise ValueError(f"Invalid environment and subtype combination.p_env_type={p_env_type},p_dev_type={p_dev_type}")
    elif upper_env_type == "SIM" and upper_dev_type not in {DevType.LEGACY.name, DevType.MODERN.name, DevType.NVME.name}:
        raise ValueError(f"Invalid environment and subtype combination.p_env_type={p_env_type},p_dev_type={p_dev_type}")
    if upper_env_type == "SIM":
        env_type = EnvironmentType.SIM
    elif upper_env_type == "EMU":
        env_type = EnvironmentType.EMU
    elif upper_env_type == "CRB":
        env_type = EnvironmentType.CRB
    elif upper_env_type == "HYBRID":
        env_type = EnvironmentType.HYBRID
    else:
        raise ValueError(f"Invalid environment error,env_type = {p_env_type}")

    if upper_dev_type == DevType.LEGACY.name:
        dev_type = DevType.LEGACY
    elif upper_dev_type == DevType.MODERN.name:
        dev_type = DevType.MODERN
    elif upper_dev_type == DevType.PACKED.name:
        dev_type = DevType.PACKED
    elif upper_dev_type == DevType.NVME.name:
        dev_type = DevType.NVME
    else:
        raise ValueError(f"Invalid device type error,dev_type = {p_dev_type}")

    itestObject = ItestObject(env_type, dev_type)
    return itestObject


def get_sim_abspath(sim_type):
    SIM_ConfAbsPath = ""
    if sim_type == DevType.LEGACY:
        SIM_ConfAbsPath = get_conf_abspath(SIM_NetBlk_Legacy_ConfPath)
    elif sim_type == DevType.MODERN:
        SIM_ConfAbsPath = get_conf_abspath(SIM_NetBlk_Modern_ConfPath)
    elif sim_type == DevType.NVME:
        SIM_ConfAbsPath = get_conf_abspath(SIM_NVMe_ConfPath)
    return SIM_ConfAbsPath


def get_config_reader(itestObject):
    # 获取配置文件的绝对路径
    config_reader = None
    env_type = itestObject.get_env_type()
    if env_type == EnvironmentType.EMU:
        EMU_ConfAbsPath = get_conf_abspath(EMU_ConfPath)
        config_reader = read_conf(EMU_ConfAbsPath)
    elif env_type == EnvironmentType.SIM:
        dev_type = itestObject.get_dev_type()
        SIM_ConfAbsPath = get_sim_abspath(dev_type)
        config_reader = read_conf(SIM_ConfAbsPath)
    elif env_type == EnvironmentType.HYBRID:
        HYBRID_ConfAbsPath = get_conf_abspath(HYBRID_ConfPath)
        config_reader = read_conf(HYBRID_ConfAbsPath)
    elif env_type == EnvironmentType.CRB:
        CRB_ConfAbsPath = get_conf_abspath(CRB_ConfPath)
        config_reader = read_conf(CRB_ConfAbsPath)
    else:
        raise ENVError(f"env 类型错误：env is {env_type},not EMU or SIM or HYBRID or CRB")

    return config_reader


class Server(object):
    def __init__(self, hostname, port, username, password):
        self._hostname = hostname
        self._port = port
        self._username = username
        self._password = password

    @property
    def hostname(self):
        return self._hostname

    @hostname.setter
    def hostname(self, value):
        self._hostname = value

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value):
        self._port = value

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, value):
        self._username = value

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        self._password = value


class ConfigReader:
    def __init__(self, config_file):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

    def get_section_options(self, section):
        if section in self.config:
            return self.config.options(section)
        else:
            return []

    def get_option_value(self, section: object, option: object) -> object:
        if section in self.config and option in self.config[section]:
            return self.config.get(section, option)
        else:
            return None

    def get_all_sections(self):
        return self.config.sections()


class ConfPage(object):
    def __init__(self, env_type, dev_type):
        self._itestObject = set_itestObject(env_type, dev_type)
        self._n2_server = None
        self._host_server = None
        self._config_reader = get_config_reader(self._itestObject)
        self.set_n2_server(self._config_reader)
        self.set_host_server(self._config_reader)

    def get_itestObject(self, env):
        return self._itestObject

    def set_n2_server(self, config_reader):
        self._n2_server = parse_server(config_reader, 'N2')

    def get_n2_server(self):
        return self._n2_server

    def set_host_server(self, config_reader: object) -> object:
        self._host_server = parse_server(config_reader, 'host')

    def get_host_server(self):
        return self._host_server


class HYBRIDConfPage(ConfPage):
    _bmc_server: Server

    def __init__(self, env, dev_type):
        super().__init__(env, dev_type)
        self._bmc_server = parse_server(self._config_reader, 'BMC')

    def set_bmc_server(self, config_reader):
        self._bmc_server = parse_server(config_reader, 'BMC')

    def get_bmc_server(self):
        return self._bmc_server


class EMUConfPage(ConfPage):
    _bmc_server: Server

    def __init__(self, env, dev_type):
        super().__init__(env, dev_type)
        self._bmc_server = parse_server(self._config_reader, 'BMC')

    def set_bmc_server(self, config_reader):
        self._bmc_server = parse_server(config_reader, 'BMC')

    def get_bmc_server(self):
        return self._bmc_server


class CRBConfPage(ConfPage):
    _bmc_server: Server

    def __init__(self, env, dev_type):
        super().__init__(env, dev_type)
        self._bmc_server = parse_server(self._config_reader, 'BMC')

    def set_bmc_server(self, config_reader):
        self._bmc_server = parse_server(config_reader, 'BMC')

    def get_bmc_server(self):
        return self._bmc_server


class SIMConfPage(ConfPage):
    def __init__(self, env, dev_type):
        super().__init__(env, dev_type)
        self._second_host_server = None
        self._second_host_server = parse_server(self._config_reader, 'host_2')

    def set_second_host_server(self, config_reader):
        self._second_host_server = parse_server(config_reader, 'host_2')

    def get_second_host_server(self):
        return self._second_host_server


def main():
    EMUConf = SIMConfPage("SIM", "NVME")
    print(EMUConf.get_n2_server())
    print(EMUConf.get_host_server())


if __name__ == "__main__":
    main()