import logging
import os

from common.Object.SolidDeploy import SolidDeploy
from common.utils.deploy_util import download_version_file, get_version_file_path


class IMUDeploy(SolidDeploy):
    def __init__(self, designated_date=None, designated_url=None, search_url=None, url_pattern=None, config=None, version_filename=None):
        super().__init__(type='IMU', designated_date=designated_date, designated_url=designated_url, search_url=search_url, url_pattern=url_pattern, config=config)
        self.version_filename = version_filename

    def deploy(self):
        # 首先下载版本文件
        version_filename = self.version_filename
        if version_filename is None:
            # 先删除残留的文件，然后再下载
            os.system(f'rm -f ./version/*')
            version_filename = download_version_file(self.configPage, self.download_url)

        # 接着scp到BMC
        '''scp crb_imu_flash_202312201634.img root@10.21.XX.XX:/tmp'''

        logging.info(f'---------------------正在拷贝版本文件到BMC-----------------------')
        cmd = f'sshpass -p {self.n2_bmc_pwd} scp -o StrictHostKeyChecking=no {get_version_file_path(folder_path="version", version_filename=version_filename)} {self.n2_bmc_username}@{self.n2_bmc_ip}:/tmp'
        logging.info(f'---------------------拷贝版本文件的命令是:{cmd}-----------------------')
        os.system(cmd)

        # 接着执行对应的命令
        '''firmware_tool.sh AP /tmp/crb_imu_flash_202312201634.img'''
        self.firmware_tool_command(version_filename, type='IMU')



