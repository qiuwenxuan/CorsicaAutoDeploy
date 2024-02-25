import logging
import time

from common.Object.ItestObject import EnvironmentType
from common.utils.exception import ENVError
from common.utils import dev_util, session_util, storage_util


def check_all_devs_is_ok(dev_list):
    for device in dev_list:
        if device['status'] != 'CC_EN':
            return False
    return True


def check_nvmepf_status(dev_list):
    matched_devices = []

    for device in dev_list:
        if (
                device['pci_dev_type'] == 'PF'
                and device['dev_type'] == 'NVME_BLK'
                and device['status'] == 'CC_EN'
        ):
            matched_devices.append(device)
    logging.info(f"\n-----------------------------matched_devices:\n {matched_devices}")
    assert matched_devices, '未匹配到设备'
    ret = check_all_devs_is_ok(matched_devices)
    return ret


def get_nvme_devs(it_session):
    n2_session = it_session.get_n2_session()
    host_session = it_session.get_host_session()
    dev_list = dev_util.get_dev_list(n2_session)

    devices_bdf = []
    for device in dev_list:
        if (
                device['pci_dev_type'] == 'PF'
                and device['dev_type'] == 'NVME_BLK'
                and device['status'] == 'CC_EN'
        ):
            devices_bdf.append(device['bdf'])
    logging.info(f"\n-----------------------------devices_bdf:\n {devices_bdf}")
    assert devices_bdf, '未匹配到设备'

    bdf = "|".join(devices_bdf)
    cmd = "ls -lh /sys/block/nvme* |grep -E '%s' |awk '{print $NF}'|awk -F '/' '{print $NF}'" % bdf
    result = host_session.execute_command(f"{cmd}")
    assert result, '未匹配到设备'
    nvme_list = result.strip().split('\n')
    logging.info(f"\n-----------------------------nvme_list:\n {nvme_list}")

    return nvme_list


def nvmepf_multidev_io(it_session, dev_type, check_final_result=True):
    # 0.pre 登录前后端成功,确认host端加载驱动成功
    n2_session, host_session = session_util.pretest(it_session, dev_type)

    # 1.scp fio配置模版文件到host侧
    storage_util.scp_fio_cfg_to_host(it_session)

    # 2.获取nvme盘的列表
    nvme_list = get_nvme_devs(it_session)

    # 3.根据nvme盘的列表完善fio配置文件
    storage_util.complete_fio_cfg(host_session, nvme_list)

    # 4.跑fio测试之前先杀死fio进程，避免已有的fio进程影响测试
    storage_util.kill_fio_process(host_session)

    # 5.跑fio测试
    storage_util.run_fio(host_session, bsrange='512B-1024k')

    # 6.获取fio的实时输出结果，确认fio已正常运行
    """
    存储设备若出现IO hang，则kill fio进程会出现kill不掉的情况，所以fio测试采用runtime=3600，
    测试过程中根据需要kill fio进程来检测是否出现IO hang的情况。
    """
    time.sleep(10)
    storage_util.get_real_time_result_of_fio(host_session)

    if check_final_result:
        # 7.跑fio 30s
        time.sleep(30)

        # 8.提前终止fio进程
        storage_util.kill_fio_process(host_session)

        # 9.查询fio结果
        storage_util.get_final_result_of_fio(host_session)


def nvmepf_multidev_reload_driver(it_session, dev_type):
    # fio流通测试
    nvmepf_multidev_io(it_session, dev_type)
    host_session = it_session.get_host_session()
    for i in range(3):
        logging.info(f"\n-----------------------------第{i}次循环-----------------------------")
        if it_session.env_type == EnvironmentType.SIM.name:
            # corsica sim环境不支持nvme的驱动卸载加载
            pass
        elif it_session.env_type == EnvironmentType.EMU.name or \
                it_session.env_type == EnvironmentType.CRB.name:
            # 1.卸载nvme驱动
            dev_util.unload_driver(host_session, dev_type)
            # 2.加载nvme驱动
            dev_util.load_driver(host_session, dev_type)
        else:
            raise ENVError("environment error")
        nvmepf_multidev_io(it_session, dev_type)


def nvmepf_multidev_host_reset(it_session, dev_type):
    # 跑起来持续的fio流
    nvmepf_multidev_io(it_session, dev_type, False)
    n2_session = it_session.get_n2_session()
    if it_session.env_type == EnvironmentType.SIM.name:
        # corsica sim环境不支持host reset
        pass
    elif it_session.env_type == EnvironmentType.EMU.name or \
            it_session.env_type == EnvironmentType.CRB.name:
        # 7.fio流量过程中，host reset操作，该函数暂未调试
        dev_util.reset_by_bmc(n2_session)
    else:
        raise ENVError("environment error")
    # host reset后进行fio流通测试
    nvmepf_multidev_io(it_session, dev_type)


def nvmepf_multidev_hotplug(it_session, dev_type):
    # 分为不带流热拔插和带流热拔插两个场景，热拔和热插操作暂未调试
    # 先测试不带流热拔插场景
    if it_session.env_type == EnvironmentType.SIM.name:
        # corsica sim环境不支持nvme设备的热拔插
        pass
    elif it_session.env_type == EnvironmentType.EMU.name or \
            it_session.env_type == EnvironmentType.CRB.name:
        # 不带流热拔nvme设备
        dev_util.detach_dev()
        # 热插nvme设备
        dev_util.attach_dev()
    else:
        raise ENVError("environment error")
    # 热拔插后，进行fio流通测试
    nvmepf_multidev_io(it_session, dev_type)

    # 再测试带流热拔插场景
    # 跑起来持续的fio流
    nvmepf_multidev_io(it_session, dev_type, False)

    if it_session.env_type == EnvironmentType.SIM.name:
        # corsica sim环境不支持nvme设备的热拔插
        pass
    elif it_session.env_type == EnvironmentType.EMU.name or \
            it_session.env_type == EnvironmentType.CRB.name:
        # 带流热拔nvme设备
        dev_util.detach_dev()
        # 热插nvme设备
        dev_util.attach_dev()
    else:
        raise ENVError("environment error")

    # 热拔插后，进行fio流通测试
    nvmepf_multidev_io(it_session, dev_type)


def nvmepf_multidev_io_forcekill_vhost(it_session, dev_type):
    # 跑起来持续的fio流
    nvmepf_multidev_io(it_session, dev_type, False)
    n2_session = it_session.get_n2_session()
    host_session = it_session.get_host_session()
    if it_session.env_type == EnvironmentType.SIM.name:
        # corsica sim环境不支持vhost进程重启
        pass
    elif it_session.env_type == EnvironmentType.EMU.name or \
            it_session.env_type == EnvironmentType.CRB.name:
        # 7.fio流量过程中，kill -9 vhost进程，该函数暂未调试
        storage_util.kill_vhost(n2_session)

        # 8.再次启动vhost进程
        storage_util.start_vhost(n2_session)
    else:
        raise ENVError("environment error")

    # 9.查看确认fio流量已恢复
    storage_util.get_real_time_result_of_fio(host_session)

    # 10.提前终止fio进程
    storage_util.kill_fio_process(host_session)

    # 11.查询fio结果
    storage_util.get_final_result_of_fio(host_session)
