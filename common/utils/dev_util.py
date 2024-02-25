import logging
import random
import time

from common.utils.exception import TYPEError, Error, ENVError
from common.utils.storage_util import reset_host, disable_rc_timeout
from common.utils.util import subprocess_command


def get_dev_type_name(dev_type):
    if dev_type == "net":
        dev_type_name = 'VIRTIO_NET'
    elif dev_type == "blk":
        dev_type_name = 'VIRTIO_BLK'
    else:
        raise TYPEError("type is error")
    return dev_type_name


def load_driver(host_session, dev_type):
    if dev_type == "net":
        cmd = f"lsmod | grep -q virtio_net || modprobe virtio_net"
    elif dev_type == "blk":
        cmd = f"lsmod | grep -q virtio_blk || modprobe virtio_blk"
    elif dev_type == "nvme":
        cmd = f"lsmod | grep -q nvme || modprobe nvme"
    else:
        raise Exception("type is error")
    result = host_session.execute_command(cmd)
    logging.info(f"\n-----------------------------驱动加载的结果是： {result}")
    assert result == ""


def unload_driver(host_session, dev_type):
    if dev_type == "net":
        cmd = f"rmmod virtio_net"
    elif dev_type == "blk":
        cmd = f"modprobe -r virtio_blk; [ $? -eq 0 ] && " \
              f"{{ lsmod | grep -q virtio_blk || echo 'unloaded successfully'; }} " \
              f"|| echo 'Failed to unload module'"
    elif dev_type == "nvme":
        cmd = f"rmmod nvme"
    else:
        raise Exception("type is error")

    timeout = 30
    start_time = time.time()
    while True:
        current_time = time.time()
        elapsed_time = current_time - start_time

        if elapsed_time > timeout:
            logging.error("超时：驱动卸载未成功")
            break

        output = host_session.execute_command(cmd).strip()
        logging.info(f"\n-----------------------------驱动卸载的结果是： {output}")
        if 'unloaded successfully' in output:
            logging.info("驱动卸载已成功")
            break

        # 间隔2秒再次卸载驱动
        time.sleep(2)


def parse_devs_str(devs_str):
    lines = devs_str.strip().split('\n')
    headers = lines[0].split()  # Extract headers from the first line
    device_list = []

    for line in lines[1:]:  # Skip the first two lines (header and dev list: line)
        values = line.split()
        device = {}  # Create a dictionary to store device information
        for idx, header in enumerate(headers):
            device[header] = values[idx]  # Assign each value to the corresponding header key
        device_list.append(device)

    return device_list


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


def get_dev_list(n2_session):
    # 1.进入后端诊断模块msg_cmd，输入查询命令device list
    ret = n2_session.shell_run(run_msg_cmd, param='device list')
    assert "device list" in ret and "dev list" in ret
    # 2 截取执行'device list'的结果，得到的devsString
    lines = ret.strip().split('\n')
    # 2.1 去掉前四行和最后一行
    trimmed_lines = lines[4:-1]
    devsString = '\n'.join(trimmed_lines)
    logging.info(f"\n-----------------------------devsString:\n {devsString}")

    # 3.把devs 字符串转化为 dev_list
    dev_list = parse_devs_str(devsString)
    logging.info(f"\n-----------------------------dev_list:\n {dev_list}")
    return dev_list


def check_all_devs_is_ok(dev_list):
    for device in dev_list:
        if device['status'] != 'DRIVER_OK':
            return False
    return True


def get_random_dev(devs):
    # 随机选择一个字典并获取其 dev_name 值
    if devs:
        random_dev = random.choice(devs)
        dev_name = random_dev.get('dev_name')
        if not dev_name:
            logging.error("dev_name isn\'t finded.")
        return random_dev
    else:
        logging.error("devs is None")
        raise Error("devs is None")


def reset_by_bmc(it_session):
    # host bmc口操作“Power reset”
    # host起来以后，加载virtio_blk驱动
    # TODO 未调试，ipmitool -I lanplus -H 10.20.25.149 -U root -P root power reset
    # host_session = it_session.get_host_session()

    # 1.获取host bmc会话
    SIMConfPage = it_session.get_configure()
    bmc_server = SIMConfPage.get_bmc_server()
    logging.info(f"bmc_server:{bmc_server.hostname},{bmc_server.username},{bmc_server.password},{bmc_server.port}")

    # 2.拼接冷重启命令
    cmd = f"ipmitool -I lanplus -H {bmc_server.hostname} -U {bmc_server.username} -P {bmc_server.password} power status"  # 重启power
    logging.info(f"\n-----------------------------执行冷重启命令:{cmd}")

    # 3.在windows调试机上启动冷重启，等待host重启成功
    res = reset_host(it_session,cmd)
    assert res, "host重启未成功"


def detach_dev(n2_session, xml_path):
    # TODO，未调试，qmp detach-device easy_bm nvme7.xml
    cmd = f"qmp detach-device easy_bm {xml_path}"
    n2_session.execute_command(cmd)


def attach_dev(n2_session, xml_path):
    # TODO，未调试，qmp attach-device easy_bm nvme7.xml
    cmd = f"qmp attach-device easy_bm {xml_path}"
    logging.info(f"\n-----------------------------热插操作命令:{cmd}")
    output = n2_session.execute_command(cmd)
    logging.info(f"\n-----------------------------热插操作输出结果:{output}")


def get_legacy_dev_by_dev_name(dev_list, dev_type):
    matched_devices = []
    dev_type_name = get_dev_type_name(dev_type)

    for device in dev_list:
        if (
                device['pci_dev_type'] == 'PF'
                and device['dev_type'] == dev_type_name
                and int(device['guest_features'], 16) & (1 << 34) == 0
                and int(device['guest_features'], 16) & (1 << 32) == 0
        ):
            matched_devices.append(device)
    if len(matched_devices) == 0:
        raise Error(f"get legacy dev error.dev_type={dev_type},dev_list={dev_list}")
    return matched_devices


def get_modern_dev_by_dev_name(dev_list, dev_type):
    matched_devices = []
    dev_type_name = get_dev_type_name(dev_type)

    for device in dev_list:
        if (
                device['pci_dev_type'] == 'PF'
                and device['dev_type'] == dev_type_name
                and (int(device['guest_features'], 16) >> 32) & 1 == 1
                and (int(device['guest_features'], 16) >> 34) & 1 == 0
        ):
            matched_devices.append(device)
    if len(matched_devices) == 0:
        raise Error(f"get modern dev error.dev_type={dev_type},dev_list={dev_list}")
    return matched_devices


def get_packed_dev_by_dev_name(dev_list, dev_type):
    matched_devices = []
    dev_type_name = get_dev_type_name(dev_type)

    for device in dev_list:
        if (
                device['pci_dev_type'] == 'PF'
                and device['dev_type'] == dev_type_name
                and int(device['guest_features'], 16) & (1 << 34) != 0
        ):
            matched_devices.append(device)
    if len(matched_devices) == 0:
        error_info = f"get packed dev error.dev_type={dev_type},dev_list={dev_list}"
        logging.error(error_info)
        raise Error(error_info)
    return matched_devices


def check_modern_pf_status(dev_list, dev_type):
    matched_devices = get_modern_dev_by_dev_name(dev_list, dev_type)
    ret = check_all_devs_is_ok(matched_devices)
    return ret


def check_packed_pf_status(dev_list, dev_type):
    matched_devices = get_packed_dev_by_dev_name(dev_list, dev_type)
    ret = check_all_devs_is_ok(matched_devices)
    return ret


def check_legacy_pf_status(dev_list, dev_type):
    matched_devices = get_legacy_dev_by_dev_name(dev_list, dev_type)
    ret = check_all_devs_is_ok(matched_devices)
    return ret


# 检查N2端dev_queue_type对应的设备是否driver ok,默认检查N2所有的设备
def check_dev_pf_status(dev_list, dev_type, dev_queue_type='all'):
    if dev_queue_type == 'legacy':
        matched_devices = get_legacy_dev_by_dev_name(dev_list, dev_type)
    elif dev_queue_type == 'modern':
        matched_devices = get_modern_dev_by_dev_name(dev_list, dev_type)
    elif dev_queue_type == 'packed':
        matched_devices = get_packed_dev_by_dev_name(dev_list, dev_type)
    elif dev_queue_type == 'all':
        matched_devices = dev_list
    else:
        raise ENVError("environment error")
    ret = check_all_devs_is_ok(matched_devices)
    return ret
