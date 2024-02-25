import logging
import os
import json
import time
import configparser

from common.base_common import ssh_run
from common.utils.dev_util import get_dev_list
from common.utils.netdev_util import ping_test_0_loss_rate

logging.basicConfig(level=logging.INFO)  # 配置日志级别为INFO


def run_msg_cmd(shell, param=None):
    command = param
    logging.info(f"run_msg_cmd:command:{command}")
    shell.su_login('jaguar')
    shell.set_default_end_list(['>> '])
    shell.run_by_auth_yes('ssh root@127.0.0.1 -p 6000', 'jmnd')
    shell.run('msg_cmd')
    ret = shell.run(command, mod='ret_only')
    logging.info(f"---------etPFPage.run_msg_cmd:ret:{ret}")
    shell.run('quit')
    shell.set_default_end_list(['# '])
    shell.run('quit')
    return ret


def get_version_file_path(folder_path):
    files = os.listdir(folder_path)
    assert len(files) == 1, 'version文件夹中没有版本文件！'
    filename = files[0]
    logging.info(f'--------------版本文件名是：{filename}----------------')
    logging.info(f'--------------方法返回值是：{os.path.abspath(filename)}----------------')
    full_file_path = os.path.join(folder_path, filename)
    return os.path.abspath(full_file_path)


def remove_suffix(text, suffix):
    if text.endswith(suffix):
        return text[: -len(suffix)]
    return text


def main():
    # 读入配置文件
    # 创建配置解析器对象
    config = configparser.ConfigParser()

    # 读取配置文件
    config.read('./config/env.conf')  # 将文件名替换为你实际的配置文件路径

    # 获取各个服务器的ip地址
    n2_ip = config.get('N2', 'hostname')
    n2_username = config.get('N2', 'username')
    n2_pwd = config.get('N2', 'password')

    host_ip = config.get('host', 'hostname')
    host_username = config.get('host', 'username')
    host_pwd = config.get('host', 'password')

    host_bmc_ip = config.get('hostBMC', 'hostname')
    host_bmc_username = config.get('hostBMC', 'username')
    host_bmc_pwd = config.get('hostBMC', 'password')
    test_prefix = ''
    # 拷贝业务版本
    logging.info('-----------------正在拷贝业务版本-----------------')
    filepath = get_version_file_path('version')
    # 先清除N2端的文件夹
    os.system(
        f"sshpass -p {n2_pwd} ssh -o StrictHostKeyChecking=no {n2_username}@{n2_ip} 'rm -rf {test_prefix}/usr/share/jmnd/*' ")
    # 接着将本地的tar.gz文件拷贝到N2
    cmd = f"sshpass -p {n2_pwd} scp {filepath} {n2_username}@{n2_ip}:{test_prefix}/usr/share "
    logging.info(f'-------------------拷贝本地版本文件tar.gz到N2的命令是：{cmd}----------------------------------')
    os.system(cmd)

    # 登录N2
    logging.info('-----------------正在登录N2-----------------')
    n2_session = ssh_run.SSHSessions(n2_ip, n2_username, n2_pwd)
    result = n2_session.connect()
    logging.info(f'------------连接N2的结果：{result}-------------')
    assert result == 0, '登录N2失败'

    # 在N2上解压
    filename = os.path.basename(filepath)
    n2_session.execute_command(f'cd {test_prefix}/usr/share && gzip -d {filename}')

    cmd = f'cd {test_prefix}/usr/share && tar -xf {remove_suffix(filename, ".gz")}'
    logging.info(f'-------------------在N2上解压缩tar文件的命令是：{cmd}----------------------------------')
    n2_session.execute_command(cmd)

    # 解压缩好了以后开始修改文件
    logging.info(f'-------------------正在修改config.json文件和修改start_basic_env.sh文件--------------------------')
    n2_session.execute_command(
        f'''cd {test_prefix}/usr/share/jmnd/config && sed -i 's/"2m_hugepages": 2048/"2m_hugepages": 8192/' config.json ''')
    n2_session.execute_command(
        f'''cd {test_prefix}/usr/share/jmnd/single/auto/script && sed -i 's/echo 2 > /echo 8 > /' start_basic_env.sh ''')

    logging.info('-----------------正在拷贝配置文件-----------------')
    # 拷贝configure文件
    file_path = "./config/cloud/bm_config.json"
    # 解析config文件
    # 从JSON文件中加载数据
    with open(file_path, 'r', encoding='utf-8') as file:
        config_data = json.load(file)

    # 判断RAW_FILE_DIR存不存在，如果不存在，需要先创建
    result = n2_session.execute_command(config_data['RAW_FILE_CFG']['RAW_FILE_DIR'])
    if 'No' in result:
        n2_session.execute_command(f'mkdir {config_data["RAW_FILE_CFG"]["RAW_FILE_DIR"]}')
    # 拷贝配置文件
    os.system(
        f"sshpass -p {n2_pwd} scp {os.path.abspath(file_path)} {n2_username}@{n2_ip}:{test_prefix}/usr/share/jmnd/single/auto/config")

    # 执行kill_all.sh
    logging.info('-----------------正在执行./kill_all.sh-----------------')
    result = n2_session.execute_command(f'cd {test_prefix}/usr/share/jmnd/single/auto/script && ./kill_all.sh')
    logging.info(f'-------------./kill_all.sh的结果：{result}--------------------')

    # 配置巨页
    logging.info('-----------------正在配置巨页-----------------')
    n2_session.execute_command('echo 8192 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages')
    n2_session.execute_command('echo 8 > /sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages')
    n2_session.execute_command('echo 1 > /sys/module/vfio/parameters/enable_unsafe_noiommu_mode')
    n2_session.execute_command('modprobe vfio-pci enable_unsafe_noiommu_mode=1')
    n2_session.execute_command('export PATH=$PATH:/usr/share/jmnd/bin/ovs/images/bin')

    # 启动业务
    logging.info('-----------------正在执行./start_all.sh-----------------')
    result = n2_session.execute_command(f'cd {test_prefix}/usr/share/jmnd/single/auto/script && ./start_all.sh ')
    logging.info(f'-------------./start_all.sh的结果：{result}--------------------')
    # 检查
    # 这里需要阻塞等待 qmp创建成功
    cnt = 10
    origin_value = cnt
    while cnt > 0:
        result = n2_session.execute_command('qmp list | grep bm_itest')
        logging.info(f'---------------第{origin_value-cnt+1}次查看qmp list，结果为:{result}----------------')
        if 'running' in result:
            break
        time.sleep(3)
        cnt -= 1
    result = n2_session.execute_command('qmp list | grep bm_itest')
    logging.info(f'---------------查看qmp list，结果为:{result}----------------')
    assert 'running' in result, 'bm qume没有在运行'

    # 进入后端，进入诊断模式
    logging.info(f'------------正在检查后端设备数量')
    dev_list = get_dev_list(n2_session)

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

    # 'Legacy'
    # matched_devices = dev_util.get_legacy_dev_by_dev_name(dev_list, "net")
    # 'Modern'
    # matched_devices = dev_util.get_modern_dev_by_dev_name(dev_list, "net")
    # 'Packed'
    # matched_devices = dev_util.get_packed_dev_by_dev_name(dev_list, "net")

    # 重启host
    logging.info(f'---------------------正在重启host-------------------------')
    # f1.ipmi_power_reset(f1, '10.21.187.92', 'admin', 'admin')
    cmd = f'ipmitool -H {host_bmc_ip} -I lanplus -U {host_bmc_username} -P {host_bmc_pwd}  power reset'
    result = n2_session.execute_command(cmd)
    logging.info(f'--------------------重启host结果:{result}-------------------------')

    # 踏步等待host重启
    logging.info(f'---------------------正在等待host重启-------------------------')
    max_wait_time = 15 * 60  # 10 分钟
    start_time = time.time()
    cnt = 0
    while True:
        cnt += 1
        if ping_test_0_loss_rate(n2_session, host_ip):
            break

        current_time = time.time()
        elapsed_time = current_time-start_time

        logging.info(f'{current_time}:-------这是第{cnt}次探测, 耗时{current_time-start_time}')

        if elapsed_time > max_wait_time:
            logging.error('host重启失败！')
            break

        time.sleep(20)

    # 前端check
    host_session = ssh_run.SSHSessions(host_ip, host_username, host_pwd)
    result = host_session.connect()
    logging.info(f'------------连接host的结果：{result}-------------')
    assert result == 0, '登录host失败'

    result = host_session.execute_command('lspci | grep -i virtio')
    logging.info(f'--------lspci | grep -i virtio 命令的返回值：{result}-------------------')
    assert result.count('block') == config_data['BLK_COUNT']
    assert result.count('network') == config_data['NET_COUNT']


if __name__ == '__main__':
    main()
