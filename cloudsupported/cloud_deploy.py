import configparser
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from common.base_common import ssh_run
from common.utils.deploy_util import download_version_file, get_version_file_path, get_download_url
from common.utils.dev_util import get_dev_list
from common.utils.netdev_util import ping_test_0_loss_rate


class CloudDeploy:

    def __init__(self, designated_date=None, designated_url=None, search_url=None, url_pattern=None, release=False,
                 config=None, jmnd_config=None, version_filename=None):
        self.designated_date = designated_date
        self.designated_url = designated_url
        self.search_url = search_url
        self.url_pattern = url_pattern
        self.release = release
        self.configFilepath = config
        self.version_filename = version_filename
        self.jmnd_config = jmnd_config
        # 读入配置文件
        self.read_config(self.search_url, self.url_pattern, self.release)
        # 登录N2并检查根目录容量
        self.login_n2()
        self.check_root_memory_capacity()
        # 下载版本文件到本机（103）
        self.download_version_file(designated_date=designated_date, designated_url=designated_url)
        self.test_prefix = ''

    def deploy(self):
        # deploy之前需要重新获取一下n2的连接，因为可能连接会被外部中断
        self.login_n2()
        # 拷贝版本文件到N2的tmp
        self.copy_version_file_2_N2()
        # 拷贝configure文件
        self.copy_conf_file_2_N2()
        # kill all
        self.kill_all()
        # 配置巨页
        self.config_huge_page()
        # start all
        self.start_all()
        # ovs bond pccu
        self.bond_pccu()
        # check N2
        self.checkN2()
        # host reset
        self.host_reset()
        # check host
        self.check_host()
        # Start trex service
        if self.jmnd_config.lower() == 'net':
            self.stop_trex()
            self.start_trex()

    def read_config(self, search_url, url_pattern, release=False):
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

        self.configPage = {'JFrogUsername': config.get('profile', 'JFrog_username'),
                           'JFrogPassword': config.get('profile', 'JFrog_password')}

        if search_url is None or search_url.lower() == 'none':
            final_search_url = config.get('cloudSupportVersionFileConfig', 'searching_url')
        else:
            final_search_url = search_url

        if url_pattern is None or url_pattern.lower() == 'none':
            if release:
                final_url_pattern = config.get('cloudSupportVersionFileConfig', 'relFilePattern')
            else:
                final_url_pattern = config.get('cloudSupportVersionFileConfig', 'filePattern')
        else:
            final_url_pattern = url_pattern

        self.versionFileConfig = {'searching_url': final_search_url,
                                  'filePattern': final_url_pattern}

    def download_version_file(self, designated_date=None, designated_url=None, download_dir='./version'):
        if self.version_filename is not None:  # 如果是--deploy-all的话，那么版本文件已经准备好了，不需要再次下载
            return
        if designated_url is None or designated_url.lower() == 'none':
            download_url = get_download_url(self.configPage, self.versionFileConfig, designated_date)
        else:
            download_url = designated_url
        # 先删除残留的文件，然后再下载
        os.system(f'rm -f ./version/*')
        self.version_filename = download_version_file(self.configPage, download_url,
                                                      download_dir)  # 将版本文件存储到对象中，拷贝版本文件时需要使用到

    def login_n2(self):
        max_retries_time = 3  # 最大尝试次数
        cnt = 0

        while True:
            logging.info('-----------------正在登录N2-----------------')
            self.n2_session = ssh_run.SSHSessions(self.n2_ip, self.n2_username, self.n2_pwd)
            result = self.n2_session.connect()
            logging.info(f'------------连接N2的结果：{result}-------------')

            if result == 0:
                break

            if cnt == max_retries_time:
                break

            # retries
            logging.info('尝试执行mdio-tool后重新登录：')
            logging.info(f'第{cnt + 1}次尝试')
            if cnt == 0:  # 第一次尝试才需要登录
                # 先登录N2 BMC
                logging.info('-----------------正在登录N2 BMC-----------------')
                self.n2_bmc_session = ssh_run.SSHSessions(self.n2_bmc_ip, self.n2_bmc_username, self.n2_bmc_pwd)
                result = self.n2_bmc_session.connect()
                logging.info(f'------------连接N2 BMC的结果：{result}-------------')
                assert result == 0, '登录N2 BMC失败'
            # 执行mdio-tool命令
            self.n2_bmc_session.execute_command('mdio-tool')
            # 阻塞10s
            time.sleep(10)
            # 重新登录
            cnt += 1

        assert result == 0, '登录N2失败'

    def login_host(self):
        logging.info('-----------------正在登录host-----------------')
        self.host_session = ssh_run.SSHSessions(self.host_ip, self.host_username, self.host_pwd)
        result = self.host_session.connect()
        logging.info(f'------------连接host的结果：{result}-------------')
        assert result == 0, '登录host失败'

    def clean_tmpversion_file_in_N2(self):
        """
        清理N2 的/var/tmp/下的所有内容
        """
        cmd = f'rm -rf /var/tmp/*'
        logging.info(f'-------------------在N2上清除tmp文件命令是：{cmd}----------------------------------')
        self.n2_session.execute_command(cmd)

        cmd = f'rm -rf /var/run/jmnd*'
        logging.info(f'-------------------在N2上清除run文件命令是：{cmd}----------------------------------')
        self.n2_session.execute_command(cmd)

    def copy_version_file_2_N2(self):
        # 拷贝业务版本
        logging.info('-----------------正在拷贝业务版本-----------------')
        filepath = get_version_file_path('version', self.version_filename)
        # 先清除N2端的文件夹
        os.system(
            f"sshpass -p {self.n2_pwd} ssh -o StrictHostKeyChecking=no {self.n2_username}@{self.n2_ip} 'rm -rf {self.test_prefix}/usr/share/jmnd/*' ")
        # 接着将本地的tar.gz文件拷贝到N2
        cmd = f"sshpass -p {self.n2_pwd} scp -o StrictHostKeyChecking=no {filepath} {self.n2_username}@{self.n2_ip}:{self.test_prefix}/tmp "
        logging.info(f'-------------------拷贝本地版本文件tar.gz到N2的命令是：{cmd}----------------------------------')
        os.system(cmd)

        # 在N2上解压
        filename = os.path.basename(filepath)
        # self.n2_session.execute_command(f'cd {self.test_prefix}/tmp && gzip -d {filename}')

        # cmd = f'cd {self.test_prefix}/tmp && tar -xf {remove_suffix(filename, ".gz")} -C {self.test_prefix}/usr/share'
        cmd = f'cd {self.test_prefix}/tmp && tar -zxvf {filename}'
        logging.info(f'-------------------在N2上解压缩tar文件的命令是：{cmd}----------------------------------')
        self.n2_session.execute_command(cmd)
        # 移动
        if self.release:
            cmd = f'cd {self.test_prefix}/tmp; mv jmnd_rel jmnd;mv /tmp/jmnd /usr/share/'
            self.n2_session.execute_command(cmd)
        else:
            cmd = f'mv /tmp/jmnd /usr/share/'
            self.n2_session.execute_command(cmd)
        # 解压缩好了以后开始修改文件
        logging.info(
            f'-------------------正在修改config.json文件和修改start_basic_env.sh文件--------------------------')
        self.n2_session.execute_command(
            f'''cd {self.test_prefix}/usr/share/jmnd/config && sed -i 's/"2m_hugepages": 2048/"2m_hugepages": 8192/' config.json ''')
        self.n2_session.execute_command(
            f'''cd {self.test_prefix}/usr/share/jmnd/single/auto/script && sed -i 's/echo 2 > /echo 8 > /' start_basic_env.sh ''')

    def copy_conf_file_2_N2(self):
        file_path = ''
        if self.jmnd_config == 'cloud':
            # 拷贝configure文件
            file_path = "./config/cloud/bm_config.json"
        elif self.jmnd_config == 'net':
            file_path = "./config/net/bm_config.json"
        # 解析config文件
        # 从JSON文件中加载数据
        with open(file_path, 'r', encoding='utf-8') as file:
            self.config_data = json.load(file)

        # 判断RAW_FILE_DIR存不存在，如果不存在，需要先创建
        result = self.n2_session.execute_command(self.config_data['RAW_FILE_CFG']['RAW_FILE_DIR'])
        if 'No' in result:
            self.n2_session.execute_command(f'mkdir {self.config_data["RAW_FILE_CFG"]["RAW_FILE_DIR"]}')
        logging.info('-----------------正在备份配置文件-----------------')
        # 拷贝配置文件前，先备份原本的文件
        cmd = f'cd /usr/share/jmnd/single/auto/config && mv bm_config.json bm_config.json.bak'
        logging.info(f'-----------------备份配置文件的命令:{cmd}-----------------')
        self.n2_session.execute_command(cmd)
        logging.info('-----------------正在拷贝配置文件-----------------')
        # 拷贝配置文件
        os.system(
            f"sshpass -p {self.n2_pwd} scp -o StrictHostKeyChecking=no {os.path.abspath(file_path)} {self.n2_username}@{self.n2_ip}:{self.test_prefix}/usr/share/jmnd/single/auto/config")

    def kill_all(self):
        # 执行kill_all.sh
        logging.info('-----------------正在执行./kill_all.sh-----------------')
        result = self.n2_session.execute_command(
            f'cd {self.test_prefix}/usr/share/jmnd/single/auto/script && ./kill_all.sh')
        logging.info(f'-------------./kill_all.sh的结果：{result}--------------------')

    def config_huge_page(self):
        # 配置巨页
        logging.info('-----------------正在配置巨页-----------------')
        self.n2_session.execute_command('echo 8192 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages')
        self.n2_session.execute_command('echo 8 > /sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages')
        self.n2_session.execute_command('echo 1 > /sys/module/vfio/parameters/enable_unsafe_noiommu_mode')
        self.n2_session.execute_command('modprobe vfio-pci enable_unsafe_noiommu_mode=1')
        self.n2_session.execute_command('export PATH=$PATH:/usr/share/jmnd/bin/ovs/images/bin')

    def start_all(self):
        # 启动业务
        logging.info('-----------------正在执行./start_all.sh-----------------')
        result = self.n2_session.execute_command(
            f'cd {self.test_prefix}/usr/share/jmnd/single/auto/script && ./start_all.sh ')
        logging.info(f'-------------./start_all.sh的结果：{result}--------------------')

    def bond_pccu(self):  # 待调试
        # N2绑定pccu口
        logging.info('----------------正在绑定pccu口------------------')

        # 删除原有的pccu口
        result = self.n2_session.execute_command('ovs-vsctl show | grep dpdk0')
        if 'Port dpdk0' in result and 'Interface dpdk0' in result:
            # 删除历史dpdk0口
            cmd_del_old_dpdk0 = "ovs-vsctl del-port br-jmnd dpdk0"
            self.n2_session.execute_command(cmd_del_old_dpdk0)

        # 提取新的pcie号并绑定pccu口
        cmd_get_pcie = r"lspci | grep -m 1 'Ethernet controller: Device 1f53:1000 (rev 01)' | grep -Po '^\S+'"
        pcie_num = self.n2_session.execute_command(cmd_get_pcie).strip()

        cmd_bind_pcie = f'dpdk-devbind.py -b vfio-pci {pcie_num}'
        self.n2_session.execute_command(cmd_bind_pcie)

        cmd_add_pccu = fr'ovs-vsctl add-port br-jmnd dpdk0 -- set Interface dpdk0 type=dpdk options:dpdk-devargs={pcie_num} options:n_txq=8 options:n_rxq=8 options:n_rxq_desc=2048 options:n_txq_desc=2048 ofport_request=1'
        self.n2_session.execute_command(cmd_add_pccu)

        # 检查pccu口是否绑定成功
        result = self.n2_session.execute_command('ovs-vsctl show | grep dpdk0')
        assert result, '绑定pccu口失败！'
        return bool(result)

    def checkN2(self):
        # 检查qmp
        result = self.n2_session.execute_command('qmp list | grep bm')
        assert 'running' in result
        logging.info(f'---------------查看qmp list，结果为:{result}----------------')
        assert 'running' in result, 'bm qume没有在运行'
        # 检查设备数量
        # 进入后端，进入诊断模式
        logging.info(f'------------正在检查后端设备数量')
        dev_list = get_dev_list(self.n2_session)

        blk_num = 0
        nvme_num = 0
        net_num = 0

        for dev in dev_list:
            if dev['dev_type'] == 'VIRTIO_BLK':
                blk_num += 1
            elif dev['dev_type'] == 'VIRTIO_NET':
                net_num += 1
            elif dev['dev_type'] == 'NVME_BLK':
                nvme_num += 1

        assert blk_num + nvme_num == self.config_data['BLK_COUNT']
        assert net_num == self.config_data['NET_COUNT']

    def host_reset(self):
        # 重启host
        logging.info(f'---------------------正在重启host-------------------------')
        # f1.ipmi_power_reset(f1, '10.21.187.92', 'admin', 'admin')
        cmd = f'ipmitool -H {self.host_bmc_ip} -I lanplus -U {self.host_bmc_username} -P {self.host_bmc_pwd}  power reset'
        result = self.n2_session.execute_command(cmd)
        logging.info(f'--------------------重启host结果:{result}-------------------------')

        time.sleep(30)

        # 踏步等待host重启
        logging.info(f'---------------------正在等待host重启-------------------------')
        max_wait_time = 15 * 60  # 10 分钟
        start_time = time.time()
        cnt = 0
        while True:
            cnt += 1
            if ping_test_0_loss_rate(self.n2_session, self.host_ip):
                break

            current_time = time.time()
            elapsed_time = current_time - start_time

            logging.info(f'{current_time}:-------这是第{cnt}次探测, 耗时{current_time - start_time}')

            if elapsed_time > max_wait_time:
                logging.error('host重启失败！')
                break

            time.sleep(20)

    def check_host(self):
        # time.sleep(10)  # 等待driver load
        self.login_host()
        result = self.host_session.execute_command('lspci | grep -i virtio')
        logging.info(f'--------lspci | grep -i virtio 命令的返回值：{result}-------------------')
        # 从bm_config.json中读取nvme设备的数量
        nvme_cnt = 0
        for nvme_status in self.config_data['NVME_SWITCH_LIST']:
            if nvme_status == 'on':
                nvme_cnt += 1
        # 前端检查
        assert result.count('block') == self.config_data['BLK_COUNT'] - nvme_cnt
        assert result.count('network') == self.config_data['NET_COUNT']

    def start_trex(self):
        logging.info(f'-----------------正在启动trex服务-------------------')
        cmd_start_trex = """tmux kill-session -t trex_server_session > /dev/null 2>&1;tmux new -s trex_server_session -d \
        && tmux send -t trex_server_session "cd /root/trex/v2.93/ && (pkill -9 t-rex-64 || true) && nohup ./t-rex-64 -i --no-scapy-server --emu >./trex.log &" Enter"""
        self.host_session.execute_command(cmd_start_trex)

        cmd_check_trex = """ps -ef | grep -c rex"""
        trex_process_num = self.host_session.execute_command(cmd_check_trex)

        result = True if int(trex_process_num) >= 2 else False
        assert result, "trex进程启动失败！"
        return result

    def stop_trex(self):
        logging.info(f'-----------------正在清理trex服务-------------------')
        cmd_stop_trex = 'tmux kill-session -t trex_server_session > /dev/null 2>&1'
        self.host_session.execute_command(cmd_stop_trex)

        cmd_check_trex = 'tmux ls | grep -q trex_server_session && echo "1" || echo "0"'
        result = self.host_session.execute_command(cmd_check_trex)

        result = bool(result)
        assert result, "trex进程启动失败！"
        return result

    def reboot_n2_by_bmc(self):
        # 重启n2
        logging.info(f'---------------------正在重启n2-------------------------')
        # f1.ipmi_power_reset(f1, '10.21.187.92', 'admin', 'admin')
        cmd = ['ipmitool', '-H', self.n2_bmc_ip, '-I', 'lanplus', '-U', self.n2_bmc_username, '-P', self.n2_bmc_pwd,
               'power', 'reset']
        result = subprocess.check_output(cmd, universal_newlines=True)
        logging.info(f'--------------------重启n2结果:{result}-------------------------')
        # 阻塞30秒，等待N2关机
        time.sleep(30)
        # 踏步等待n2重启
        logging.info(f'---------------------正在等待n2重启-------------------------')
        # 先登录N2 BMC
        logging.info('-----------------正在登录N2 BMC-----------------')
        self.n2_bmc_session = ssh_run.SSHSessions(self.n2_bmc_ip, self.n2_bmc_username, self.n2_bmc_pwd)
        result = self.n2_bmc_session.connect()
        logging.info(f'------------连接N2 BMC的结果：{result}-------------')
        assert result == 0, '登录N2 BMC失败'

        max_wait_time = 15 * 60  # 15 分钟
        interval = 20  # 每次循环阻塞的时间
        mdio_wait_time = 2 * 60  # 2 分钟
        mdio_start_time = time.time()
        start_time = time.time()

        mdio_tool_cmd = 'mdio-tool'
        cnt = 0
        while True:
            cnt += 1
            # 在ping之前，先在bmc上执行mdio-tool命令
            current_time = time.time()
            elapsed_time = current_time - mdio_start_time
            if elapsed_time > mdio_wait_time:
                logging.info(f'------------正在n2 bmc上执行命令：{mdio_tool_cmd}-------------')
                mdio_start_time = current_time  # 相当于是重置计时器
                self.n2_bmc_session.execute_command(mdio_tool_cmd)

            time.sleep(interval)

            if self.local_ping_n2_loss_rate(self.n2_ip):
                break

            current_time = time.time()
            elapsed_time = current_time - start_time

            logging.info(f'{current_time}:-------这是第{cnt}次探测, 耗时{current_time - start_time}')

            if elapsed_time > max_wait_time:
                logging.error('n2重启失败！')
                break

    def check_root_memory_capacity(self):
        # 部署前清理N2 前一个版本的临时文件
        self.clean_tmpversion_file_in_N2()
        logging.info(f'---------------------正在检查根目录容量-------------------------')
        cmd = "df -h | grep '/$' | awk '{print $4}' "
        memory_capacity = self.n2_session.execute_command(cmd).strip()
        logging.info(f'---------------------根目录容量是{memory_capacity}-------------------------')
        unit = memory_capacity[-1]  # 获取容量的单位
        need_reboot = False
        if unit == 'M':  # 如果容量小到用M来描述容量
            need_reboot = True
        elif unit == 'G' and float(memory_capacity[:-1]) < 3:
            need_reboot = True
        elif unit == '0':  # 如果容量为0，不显示单位，但是此时也需要reboot
            need_reboot = True

        if need_reboot:
            self.reboot_n2_by_bmc()
            self.login_n2()  # 重新登陆

    def local_ping_n2_loss_rate(self, target_ip):
        cmd = f"ping {target_ip} -c 1 " + "|grep loss|awk '{print $6}'|awk -F \"%\" '{print $1}'"
        ping_output = subprocess.check_output(cmd, shell=True, universal_newlines=True)
        logging.info(f'-----------------execute command is {cmd}--ping_output is ' + ping_output)
        if ping_output.strip() == '0':
            return True
        else:
            return False


def recover_bm_config(config_filepath=None):  # 使用bm_config.json.bak恢复配置文件
    # 首先读入配置
    # 创建配置解析器对象
    config = configparser.ConfigParser()

    # 读取配置文件
    config_filepath = './config/env.conf' if config_filepath is None else config_filepath
    config.read(config_filepath)  # 将文件名替换为你实际的配置文件路径

    # 获取n2服务器的ip地址
    n2_ip = config.get('N2', 'hostname')
    n2_username = config.get('N2', 'username')
    n2_pwd = config.get('N2', 'password')

    # 登录n2
    logging.info('-----------------正在登录N2-----------------')
    n2_session = ssh_run.SSHSessions(n2_ip, n2_username, n2_pwd)
    result = n2_session.connect()
    logging.info(f'------------连接N2的结果：{result}-------------')
    assert result == 0, '登录N2失败'

    # 执行恢复备份命令
    logging.info('-----------------正在恢复备份-----------------')

    logging.info('-----------------查看jmnd/single/auto/config文件夹下的文件:-----------------')
    cmd = f'ls /usr/share/jmnd/single/auto/config'
    result = n2_session.execute_command(cmd)
    logging.info(f'--------------执行的命令是{cmd}, 命令的返回结果是:{result}')
    # 检查有无备份文件
    cmd = f'ls /usr/share/jmnd/single/auto/config | grep bm_config.json.bak'
    result = n2_session.execute_command(cmd)
    assert result, '无法备份，文件夹/usr/share/jmnd/single/auto/config下没有bak文件'

    # 开始备份
    cmd = f'cd /usr/share/jmnd/single/auto/config && cp -f bm_config.json.bak bm_config.json'
    logging.info(f'-----------------恢复备份的命令是:{cmd}-----------------')
    n2_session.execute_command(cmd)

    # 检查有无恢复备份成功
    # cmd = f'ls /usr/share/jmnd/single/auto/config | grep bm_config.json.bak'
    # result = n2_session.execute_command(cmd)
    # assert not result, '备份失败，文件夹/usr/share/jmnd/single/auto/config下还有bak文件'
