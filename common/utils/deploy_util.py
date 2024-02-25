import configparser
import logging
import os
import re
import subprocess
import time
import requests

from urllib.parse import urlparse
from bs4 import BeautifulSoup
from common.base_common import ssh_run


def download_version_file(configPage,url, download_dir='./version'):
    # 获取最新的下载链接
    cmd = f'wget --user {configPage["JFrogUsername"]} --password {configPage["JFrogPassword"]} -P {download_dir} {url}'
    logging.info(f'---------------------下载版本文件的命令是:{cmd}-----------------------')
    os.system(cmd)

    # 将版本文件名从下载url中提取出来
    # 解析URL
    parsed_url = urlparse(url)
    # 提取文件名（包括后缀名）
    version_filename = os.path.basename(parsed_url.path)    # 将版本文件存储到对象中，拷贝版本文件时需要使用到
    logging.info(f'----------下载的版本文件的文件名为:{version_filename}')
    return version_filename


def get_version_file_path(folder_path, version_filename):
    logging.info(f'存储版本文件的文件夹是：{folder_path}')
    logging.info(f'--------------版本文件名是：{version_filename}----------------')
    full_file_path = os.path.join(folder_path, version_filename)
    logging.info(f'--------------方法返回值是：{os.path.abspath(full_file_path)}----------------')
    return os.path.abspath(full_file_path)


def login(ip, username, pwd, type='N2'):
    logging.info(f'-----------------正在登录{type}-----------------')
    session = ssh_run.SSHSessions(ip, username, pwd)
    result = session.connect()
    logging.info(f'------------连接{type}的结果：{result}-------------')
    assert result == 0, f'登录{type}失败!'
    return session


def get_download_url(configPage, versionFileConfig, designated_date=None):
    is_latest = designated_date is None
    # 首先requests.get获取index.html
    s = requests.session()
    s.auth = (configPage["JFrogUsername"], configPage["JFrogPassword"])  # 定义用户名和密码
    req = s.get(versionFileConfig["searching_url"])  # 发起get请求
    html_content = req.text  # 返回网页内容，类型为字符串
    # 使用beautiful soup解析
    logging.info('------------------已经下载完成html，html的文件内容为:----------------------')
    logging.info(html_content)
    logging.info('------------------开始解析html，获取下载地址----------------------')
    soup = BeautifulSoup(html_content, 'html.parser')
    links = soup.find_all('a')

    file_date = None
    if is_latest:
        file_date = links[-1].getText()[:-1]
    else:
        for link in links:
            temp_date = link.getText()[:-1]
            if temp_date == designated_date:
                file_date = temp_date
                break

    logging.info(f'-------------解析到的a标签链接为:{file_date}------------------')
    assert file_date is not None, f'找不到指定的日期文件，指定的日期为：{designated_date}'

    logging.info(f'-------------找到的下载日期为:{file_date}------------------')

    # 将找到的日期拼接到版本文件的下载地址中
    download_url = replace_variables(versionFileConfig['filePattern'], file_date)
    return download_url


def replace_variables(url, value):
    pattern = r"@{(.*?)}"
    matches = re.findall(pattern, url)

    assert len(matches) > 0, '找不到匹配的模式'
    url = url.replace("@{" + matches[0] + "}", value)

    return url

def reboot_n2_by_bmc(config_filepath=None):
    # 首先读入配置
    # 创建配置解析器对象
    config = configparser.ConfigParser()

    # 读取配置文件
    config_filepath = './config/env.conf' if config_filepath is None else config_filepath
    config.read(config_filepath)  # 将文件名替换为你实际的配置文件路径

    # 获取n2服务器的ip地址
    n2_ip = config.get('N2', 'hostname')
    
    # 获取n2_bmc服务器的ip地址
    n2_bmc_ip = config.get('N2BMC', 'hostname')
    n2_bmc_username = config.get('N2BMC', 'username')
    n2_bmc_pwd = config.get('N2BMC', 'password')
    
    # 重启n2
    logging.info(f'---------------------正在重启n2-------------------------')
    # f1.ipmi_power_reset(f1, '10.21.187.92', 'admin', 'admin')
    cmd = ['ipmitool', '-H', n2_bmc_ip, '-I', 'lanplus', '-U', n2_bmc_username, '-P', n2_bmc_pwd, 'power', 'reset']
    result = subprocess.check_output(cmd, universal_newlines=True)
    logging.info(f'--------------------重启n2结果:{result}-------------------------')
    # 阻塞30秒，等待N2关机
    time.sleep(30)
    # 踏步等待n2重启
    logging.info(f'---------------------正在等待n2重启-------------------------')
    # 先登录N2 BMC
    logging.info('-----------------正在登录N2 BMC-----------------')
    n2_bmc_session = ssh_run.SSHSessions(n2_bmc_ip, n2_bmc_username, n2_bmc_pwd)
    result = n2_bmc_session.connect()
    logging.info(f'------------连接N2 BMC的结果：{result}-------------')
    assert result == 0, '登录N2 BMC失败'

    max_wait_time = 15 * 60  # 15 分钟
    interval = 20   # 每次循环阻塞的时间
    mdio_wait_time = 2 * 60   # 2 分钟
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
            n2_bmc_session.execute_command(mdio_tool_cmd)

        time.sleep(interval)

        if local_ping_n2_loss_rate(n2_ip):
            break

        current_time = time.time()
        elapsed_time = current_time - start_time

        logging.info(f'{current_time}:-------这是第{cnt}次探测, 耗时{current_time - start_time}')

        if elapsed_time > max_wait_time:
            logging.error('n2重启失败！')
            break
            
def local_ping_n2_loss_rate(target_ip):
    cmd = f"ping {target_ip} -c 1 " + "|grep loss|awk '{print $6}'|awk -F \"%\" '{print $1}'"
    ping_output = subprocess.check_output(cmd,shell=True ,universal_newlines=True)
    logging.info(f'-----------------execute command is {cmd}--ping_output is ' + ping_output)
    if ping_output.strip() == '0':
        return True
    else:
        return False

def dowload_all_file(cloud_url=None, scp_url=None, imu_url=None, cloud_downloadDate=None, scp_downloadDate=None, imu_downloadDate=None, config_filepath='./config/env.conf', release=False):
    # 先读取配置文件，得到JFrog的用户名和密码
    configPage, cloud_versionFileConfig, imu_versionFileConfig, scp_versionFileConfig = get_JFrogConfigPage(config_filepath=config_filepath, release=release)
    # 先准备好下载的地址
    cloud_url = get_download_url(configPage=configPage, versionFileConfig=cloud_versionFileConfig, designated_date=cloud_downloadDate) if cloud_url is None else cloud_url
    imu_url = get_download_url(configPage=configPage, versionFileConfig=imu_versionFileConfig, designated_date=imu_downloadDate) if imu_url is None else imu_url
    scp_url = get_download_url(configPage=configPage, versionFileConfig=scp_versionFileConfig, designated_date=scp_downloadDate) if scp_url is None else scp_url
    # 下载版本文件
    cloud_version_filename = download_version_file(configPage=configPage, url=cloud_url)
    imu_version_filename = download_version_file(configPage=configPage, url=imu_url)
    scp_version_filename = download_version_file(configPage=configPage, url=scp_url)
    # 返回三个版本文件的文件名
    return cloud_version_filename, imu_version_filename, scp_version_filename


def get_JFrogConfigPage(config_filepath='./config/env.conf', release=False):
    # 读入配置文件
    # 创建配置解析器对象
    config = configparser.ConfigParser()

    # 读取配置文件
    config.read(config_filepath)  # 将文件名替换为你实际的配置文件路径
    # 获取JFrog用户名和密码
    configPage = {'JFrogUsername': config.get('profile', 'JFrog_username'),
                       'JFrogPassword': config.get('profile', 'JFrog_password')}
    # cloud support的版本文件的下载配置
    if release:
        cloud_url_pattern = config.get('cloudSupportVersionFileConfig', 'relFilePattern')
    else:
        cloud_url_pattern = config.get('cloudSupportVersionFileConfig', 'filePattern')
    cloud_versionFileConfig = {'searching_url': config.get('cloudSupportVersionFileConfig', 'searching_url'),
                               'filePattern': cloud_url_pattern}
    # imu的版本文件下载配置
    imu_versionFileConfig = {'searching_url': config.get('imuVersionFileConfig', 'searching_url'),
                               'filePattern': config.get('imuVersionFileConfig', 'filePattern')}
    # scp的版本文件下载配置
    scp_versionFileConfig = {'searching_url': config.get('scpVersionFileConfig', 'searching_url'),
                             'filePattern': config.get('scpVersionFileConfig', 'filePattern')}

    return configPage, cloud_versionFileConfig, imu_versionFileConfig, scp_versionFileConfig