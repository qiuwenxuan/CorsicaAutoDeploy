from common.Object.ConfPage import SIMConfPage
import logging
import os

from common.utils import dev_util

"""
relative_path
"""
SIM_NetBlk_Legacy_ConfPath = '/config/SIM-NetBlk-Legacy.conf'
SIM_NetBlk_Modern_ConfPath = '/config/SIM-NetBlk-Modern.conf'
SIM_NVMe_ConfPath = '/config/SIM-Nvme.conf'


def get_sim_conf(type):
    conf = SIMConfPage()
    logging.info(f"--------------type：{type}")
    parentdir = os.path.dirname(os.path.abspath(__file__))
    Confdir = f"{parentdir}/../../"
    logging.info(f"Current parentdir:{parentdir}")
    if type == "NetBlkLegacy":
        SIM_NetBlk_Legacy_ConfAbsPath = f"{Confdir}{SIM_NetBlk_Legacy_ConfPath}"
        assert os.path.exists(SIM_NetBlk_Legacy_ConfPath)
        logging.info(f"SIM_NetBlk_Legacy_ConfAbsPath is not exists."
                     f"type：{type},SIM_NetBlk_Legacy_ConfAbsPath:{SIM_NetBlk_Legacy_ConfAbsPath}")
        conf.get_sim_conf(SIM_NetBlk_Legacy_ConfPath)
    elif type == "NetBlkModern":
        SIM_NetBlk_Modern_ConfAbsPath = f"{Confdir}{SIM_NetBlk_Modern_ConfPath}"
        logging.info(f"--------------type：{type},SIM_NetBlk_Modern_ConfAbsPath:{SIM_NetBlk_Modern_ConfAbsPath}")
        assert os.path.exists(SIM_NetBlk_Modern_ConfAbsPath)
        conf.get_sim_conf(SIM_NetBlk_Modern_ConfAbsPath)
    elif type == "Nvme":
        SIM_Nvme_ConfAbsPath = f"{Confdir}{SIM_NVMe_ConfPath}"
        logging.info(f"--------------type：{type},SIM_Nvme_ConfAbsPath:{SIM_Nvme_ConfAbsPath}")
        assert os.path.exists(SIM_Nvme_ConfAbsPath)
        conf.get_sim_conf(SIM_Nvme_ConfAbsPath)
    else:
        logging.info(f"type：{type} is error.")
        assert False
    logging.info(f"完成读取配置文件")
    return conf


def pretest(it_session, dev_type):
    #  获取N2_SSHSession
    n2_session = it_session.get_n2_session()
    assert n2_session.connect() == 0
    # 获取host_SSHSession
    host_session = it_session.get_host_session()
    assert host_session.connect() == 0
    logging.info(f"N2_SSHSession:{host_session.client},host_SSHSession:{host_session.client}")
    # host端加载驱动
    dev_util.load_driver(host_session, dev_type)
    return n2_session, host_session
