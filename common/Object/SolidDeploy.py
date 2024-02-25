import configparser
import logging
import time

from tqdm import tqdm

from common.utils.deploy_util import login, get_download_url


class SolidDeploy:
    def __init__(self, type = 'IMU', designated_date=None, designated_url=None, search_url=None, url_pattern=None, config=None):
        self.type = type
        self.configFilepath = config
        # 读入配置文件
        self.read_config(search_url, url_pattern)
        # 登录N2BMC
        self.n2_bmc_session = login(self.n2_bmc_ip, self.n2_bmc_username, self.n2_bmc_pwd, type='N2Bmc')
        # 配置下载地址
        if designated_url is None or designated_url.lower() == 'none':
            self.download_url = get_download_url(self.configPage, self.versionFileConfig, designated_date)
        else:
            self.download_url = designated_url


    def read_config(self, search_url=None, url_pattern=None):
        # 读入配置文件
        # 创建配置解析器对象
        config = configparser.ConfigParser()

        # 读取配置文件
        config_filepath = './config/env.conf' if self.configFilepath is None else self.configFilepath
        config.read(config_filepath)  # 将文件名替换为你实际的配置文件路径

        # 获取各个服务器的ip地址
        self.n2_ip = config.get('N2', 'hostname')
        self.n2_username = config.get('N2', 'username')
        self.n2_pwd = config.get('N2', 'password')

        self.host_ip = config.get('host', 'hostname')
        self.host_username = config.get('host', 'username')
        self.host_pwd = config.get('host', 'password')

        self.host_bmc_ip = config.get('hostBMC', 'hostname')
        self.host_bmc_username = config.get('hostBMC', 'username')
        self.host_bmc_pwd = config.get('hostBMC', 'password')

        self.n2_bmc_ip = config.get('N2BMC', 'hostname')
        self.n2_bmc_username = config.get('N2BMC', 'username')
        self.n2_bmc_pwd = config.get('N2BMC', 'password')

        self.configPage = {'JFrogUsername': config.get('profile', 'JFrog_username'), 'JFrogPassword': config.get('profile', 'JFrog_password')}
        if self.type == 'IMU':
            if search_url is None or search_url.lower() == 'none':
                final_search_url = config.get('imuVersionFileConfig', 'searching_url')
            else:
                final_search_url = search_url

            if url_pattern is None or url_pattern.lower() == 'none':
                final_url_pattern = config.get('imuVersionFileConfig', 'filePattern')
            else:
                final_url_pattern = url_pattern

            self.versionFileConfig = {'searching_url': final_search_url,
                                      'filePattern': final_url_pattern}

            self.log_filepath = config.get('log_output_path', 'imu_log_filepath')

        elif self.type == 'SCP':
            if search_url is None or search_url.lower() == 'none':
                final_search_url = config.get('scpVersionFileConfig', 'searching_url')
            else:
                final_search_url = search_url

            if url_pattern is None or url_pattern.lower() == 'none':
                final_url_pattern = config.get('scpVersionFileConfig', 'filePattern')
            else:
                final_url_pattern = url_pattern

            self.versionFileConfig = {'searching_url': final_search_url,
                                      'filePattern': final_url_pattern}

            self.log_filepath = config.get('log_output_path', 'scp_log_filepath')

    def firmware_tool_command(self, version_filename, type='IMU'):
        self.launch_firmware_tool(version_filename,type)    # 在N2BMC后台运行fireware.sh

        time.sleep(5)   # 先等待firmware.sh跑起来
        # firmware.sh总共会经历三个阶段
        self.processBar(stage='Erasing blocks')
        self.processBar(stage='Writing data')
        self.processBar(stage='Verifying data')

        assert self.check_deploy_completed(type), f'{type}环境部署失败！'   # 最终检查一下

    def launch_firmware_tool(self, version_filename, type='IMU'):
        # logging.info(f'---------------------正在执行命令time.sleep-----------------------')
        # time.sleep(10)
        arg = 'AP' if type == 'IMU' else 'SCP'
        cmd = f'firmware_tool.sh {arg} /tmp/{version_filename} > {self.log_filepath} &'
        logging.info(f'---------------------正在执行命令{cmd}-----------------------')
        result = self.n2_bmc_session.execute_command(cmd)
        logging.info(f'---------------------命令返回结果{result}-----------------------')

    def check_deploy_completed(self, type='IMU'):
        log_filepath = '/tmp/imu_deploy.log' if type == 'IMU' else '/tmp/scp_deploy.log'

        logging.info(f'---------------------正在查询{log_filepath}-----------------------')
        cmd = f'cat {log_filepath}'
        result = self.n2_bmc_session.execute_command(cmd)
        logging.info(f'---------------------命令返回结果{result}-----------------------')

        if 'successfully' in result:
            return True
        else:
            return False

    def processBar(self, stage):
        previous_progress = 0
        current_progress = 0
        with tqdm(total=100, desc=stage, unit="%") as pbar:
            while current_progress < 100:
                current_progress = self.get_progress(stage)

                increase_progress = current_progress - previous_progress
                pbar.update(increase_progress)

                previous_progress = current_progress
                time.sleep(1)


    def get_progress(self, stage):     # 获取进度
        # logging.info(f'---------------------正在查询{stage}的进度-----------------------')
        cmd = f'tail {self.log_filepath} | grep "{stage}"' + " | awk '{gsub(/[\(\)%]/,\"\",$NF); print $NF}'"
        # logging.info(f'---------------------查询的命令是{cmd}-----------------------')
        result = self.n2_bmc_session.execute_command(cmd)
        # logging.info(f'---------------------查询的结果为{result}-----------------------')
        return int(result)