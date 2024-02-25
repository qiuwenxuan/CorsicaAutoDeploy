import logging
import time
import random
import xml.etree.ElementTree as ET
import os

from common.base_common import sftp_util
from common.Object.DiskXMLGenerator import DiskXMLGenerator
from common.Object.ItestObject import EnvironmentType
from common.utils.dev_util import load_driver
from common.utils.exception import GetVirtioBlkError, ENVError, TYPEError
from common.utils import dev_util, session_util, storage_util
from common.utils.easy_bm_parser import EasyBmParser
from common.utils.storage_util import check_vhost, disable_rc_timeout
from common.utils.util import download_file_from_n2, scp_file_to_n2


def check_blk_dev_driver_ok(it_session, dev_type, dev_queue_type):
    n2_session, host_session = session_util.pretest(it_session, dev_type)
    # 检查N2端dev_type设备是否都是DRIVER_OK

    # 1. 进入后端诊断模块msg_cmd，输入查询命令device list
    dev_list = dev_util.get_dev_list(n2_session)

    # 2.查看split 队列类型的BLK PF设备状态是否OK。
    ret = dev_util.check_dev_pf_status(dev_list, dev_type)
    assert ret, "split队列设备状态不为driver ok"

    logging.info(f"test_blkpf_{dev_queue_type}_driver_ok pass")


def get_host_blk_dev(host_name, host_session):
    # 1. 执行”ll /sys/class/block/vd*“ 命令
    cmd = f'ls -l /sys/class/block/vd*'
    result = host_session.execute_command(cmd)
    logging.info(f"\n execute_command({cmd}):\n {result}")

    # 2. 解析 blkdev
    virtio_blocks = []
    net_lines = result.strip().split('\n')
    for line in net_lines:
        # 在 Virtio blk的设备名通常以 "v" 或 "virtio" 开头
        if 'virtio' in line:
            parts = line.split('/')
            if len(parts) >= 4:
                blkdev = {'host_name': host_name, 'dev_name': parts[-1], 'pcie_num': parts[-4].split(':', 1)[-1]}
                virtio_blocks.append(blkdev)
    logging.info(f"------------------------------------virtio_blk:\n {virtio_blocks}")
    if virtio_blocks is None:
        logging.error(f"virtio_blocks is None")
        raise GetVirtioBlkError("get virtio_blocks error")

    return virtio_blocks


def check_host_blk_dev(host_name, host_session, num):
    host_dev_lists = get_host_blk_dev(host_name, host_session)
    if num == len(host_dev_lists):
        return True
    return False


def get_host_blk_dev_for_fio(it_session, dev_type, dev_queue_type):
    host_session = it_session.get_host_session()
    n2_session = it_session.get_n2_session()
    blk_dev_list = []
    if it_session.env_type == EnvironmentType.SIM.name:
        virtio_blocks = get_host_blk_dev("host", host_session)
        for dev in virtio_blocks:
            blk_dev_list.append(dev['dev_name'])
    elif it_session.env_type == EnvironmentType.EMU.name or \
            it_session.env_type == EnvironmentType.HYBRID.name or \
            it_session.env_type == EnvironmentType.CRB.name:
        # 1. 进入后端诊断模块msg_cmd，输入查询命令device list,并把结果解析。
        dev_list = dev_util.get_dev_list(n2_session)
        matched_devices = []
        if dev_queue_type == 'Legacy':
            matched_devices = dev_util.get_legacy_dev_by_dev_name(dev_list, dev_type)
        if dev_queue_type == 'Modern':
            matched_devices = dev_util.get_modern_dev_by_dev_name(dev_list, dev_type)
        if dev_queue_type == 'Packed':
            matched_devices = dev_util.get_packed_dev_by_dev_name(dev_list, dev_type)

        # 匹配出合适的legacy vdx
        matched_virtio_blk = []
        virtio_blocks = get_host_blk_dev("host", host_session)
        logging.info(f'dev_queue_type:{dev_queue_type},matched_devices is:\n{matched_devices}\n'
                     f'virtio_blocks is:\n{virtio_blocks}')
        for dev in virtio_blocks:
            for matched_dev in matched_devices:
                if dev['pcie_num'] == matched_dev['bdf']:
                    matched_dev['host_dev_name'] = dev['dev_name']
        logging.info(f'matched_virtio_blk={matched_virtio_blk}')

        blk_dev_list = []
        for dev in matched_devices:
            blk_dev_list.append(dev['host_dev_name'])
    else:
        raise ENVError("environment error")
    logging.info(f"\n-----------------------------跑fio的blk_dev_list:\n {blk_dev_list}")
    return blk_dev_list


# 以列表嵌套字典的形式返回所有满足对应前后端设备的dev_name:dbf_num
def get_host_blk_dev_dict_for_fio(it_session, dev_type, dev_queue_type):
    host_session = it_session.get_host_session()
    n2_session = it_session.get_n2_session()
    blk_dev_list = []
    if it_session.env_type == EnvironmentType.SIM.name:
        virtio_blocks = get_host_blk_dev("host", host_session)
        for dev in virtio_blocks:
            blk_dev_list.append(dev['dev_name'])
    elif it_session.env_type == EnvironmentType.EMU.name or \
            it_session.env_type == EnvironmentType.HYBRID.name or \
            it_session.env_type == EnvironmentType.CRB.name:
        # 1. 进入后端诊断模块msg_cmd，输入查询命令device list,并把结果解析
        # 所有的N2诊断模式获取的所有device list
        dev_list = dev_util.get_dev_list(n2_session)

        # 在dev_list中过滤出满足后端环境的设备matched_devices
        matched_devices = []

        if dev_queue_type == 'Legacy':
            matched_devices = dev_util.get_legacy_dev_by_dev_name(dev_list, dev_type)
        if dev_queue_type == 'Modern':
            matched_devices = dev_util.get_modern_dev_by_dev_name(dev_list, dev_type)
        if dev_queue_type == 'Packed':
            matched_devices = dev_util.get_packed_dev_by_dev_name(dev_list, dev_type)

        # 获取host端设备信息和对应的host_name、dev_name、pcie_num
        virtio_blocks = get_host_blk_dev("host", host_session)
        logging.info(f'dev_queue_type:{dev_queue_type},matched_devices is:\n{matched_devices}\n'
                     f'virtio_blocks is:\n{virtio_blocks}')
        # 将host端的pcie_num与N2端的bdf号做匹配，匹配到后将dev设备name放入matched_dev字典
        # blkdev = {'host_name': host_name, 'dev_name': parts[-1], 'pcie_num': parts[-4].split(':', 1)[-1]}
        # virtio_blocks.append(blkdev)
        for dev in virtio_blocks:
            for matched_dev in matched_devices:
                if dev['pcie_num'] == matched_dev['bdf']:
                    blk_dev_list.append({dev['dev_name']: matched_dev['bdf']})
        logging.info(f'matched_virtio_blk_bdf={blk_dev_list}')
    else:
        raise ENVError("environment error")
    # blk_dev_list为和host端匹配到的最终考验执行操作的设备
    logging.info(f"\n-----------------------------跑fio的blk_dev_list:\n {blk_dev_list}")
    return blk_dev_list


def blk_run_fio(it_session, blk_dev_list, fio_bsrange='512B-1024k', check_final_result=True):
    host_session = it_session.get_host_session()
    #  1.scp fio配置模版文件到host侧
    storage_util.scp_fio_cfg_to_host(it_session)
    storage_util.complete_fio_cfg(host_session, blk_dev_list)

    # 2.跑fio测试之前先杀死fio进程，避免已有的fio进程影响测试
    storage_util.kill_fio_process(host_session)

    # 4.跑fio测试
    storage_util.run_fio(host_session, bsrange=fio_bsrange)

    # 5.获取fio的实时输出结果，确认fio已正常运行
    time.sleep(5)
    timeout = 30
    start_time = time.time()
    while True:
        current_time = time.time()
        elapsed_time = current_time - start_time

        if elapsed_time > timeout:
            logging.error("超时：fio测试未正常运行")
            break

        # 获取fio的实时输出结果
        result = storage_util.get_result_of_fio(host_session)

        if result:
            logging.info("fio测试已正常运行")
            break

        # 间隔10秒再次获取实时结果
        time.sleep(2)

    if check_final_result:
        # 7.跑fio 30s
        time.sleep(30)

        # 8.提前终止fio进程
        storage_util.kill_fio_process(host_session)

        # 9.查询fio结果
        storage_util.get_final_result_of_fio(host_session)
        return True


# 传入一个或多个设备名称发流
def blk_run_fio_by_dev_name(it_session, blk_dev_list, check_final_result=True):
    if it_session.env_type == EnvironmentType.SIM.name:
        blk_run_fio(it_session, blk_dev_list, "512B-1024k", check_final_result)
    elif it_session.env_type == EnvironmentType.EMU.name or it_session.env_type == EnvironmentType.CRB.name:
        blk_run_fio(it_session, blk_dev_list, "4k-4k", check_final_result)
    elif it_session.env_type == EnvironmentType.HYBRID.name:
        blk_run_fio(it_session, blk_dev_list, "4k-4k", check_final_result)
    else:
        # raise ENVError("environment error")
        raise TypeError(f"it_session.env_type error.it_session.env_type={it_session.env_type}")


def blkpf_multidev_io(it_session, dev_type, dev_queue_type, check_final_result=True):
    # 0.pre 登录前后端成功,确认host端加载驱动成功
    n2_session, host_session = session_util.pretest(it_session, dev_type)
    blk_dev_list = []
    # 获取所有满足dev_queue_type环境条件的设备名
    blk_dev_lists = get_host_blk_dev_dict_for_fio(it_session, dev_type, dev_queue_type)
    logging.info(f"\n-----------------------------选择热拔的设备：{blk_dev_lists}")
    for b in blk_dev_lists:
        blk_dev_list.append(list(b.keys())[0])

    # 满足环境条件的设备全部发流
    blk_run_fio_by_dev_name(it_session, blk_dev_list, check_final_result)


def blkpf_singledev_io(it_session, dev_type, dev_queue_type, check_final_result=True):
    # 0.pre 登录前后端成功,确认host端加载驱动成功
    n2_session, host_session = session_util.pretest(it_session, dev_type)

    # 获取所有满足条件的设备以列表嵌套字典的形式输出，格式为 dev_name:bdf
    blk_dev_lists = get_host_blk_dev_dict_for_fio(it_session, dev_type, dev_queue_type)

    # 随机在blk_dev_list里选择一个满足条件的设备，获取设备的dev_name和bdf
    blk_dev_dict = random.choice(blk_dev_lists)
    blk_dev = list(blk_dev_dict.keys())[0]
    dev_bdf = blk_dev_dict[blk_dev]

    logging.info(f"\n-----------------------------选择热拔的单个设备:bdf {blk_dev}：{dev_bdf}")

    # 传入对选中的单个设备发流
    blk_run_fio_by_dev_name(it_session, blk_dev, check_final_result)

    # 返回选中的设备
    return blk_dev_dict


def blkpf_multidev_reload_driver(it_session, dev_type, dev_queue_type):
    # fio流通测试
    blkpf_multidev_io(it_session, dev_type, dev_queue_type)
    host_session = it_session.get_host_session()

    for i in range(1, 4):
        logging.info(f"\n-----------------------------第{i}次循环-----------------------------")
        if it_session.env_type == EnvironmentType.SIM.name:
            # corsica sim环境不支持virtio-blk的驱动卸载加载
            pass
        elif it_session.env_type == EnvironmentType.EMU.name or \
                it_session.env_type == EnvironmentType.HYBRID.name or \
                it_session.env_type == EnvironmentType.CRB.name:
            # 1.卸载virtio-blk驱动
            dev_util.unload_driver(host_session, dev_type)

            # 2.加载virtio-blk驱动
            dev_util.load_driver(host_session, dev_type)

        else:
            raise TypeError(f"it_session.env_type error.it_session.env_type={it_session.env_type}")
    blkpf_multidev_io(it_session, dev_type, dev_queue_type)


def blkpf_multidev_host_reset(it_session, dev_type, dev_queue_type):
    # 跑起来持续的fio流
    host_session = it_session.get_host_session()
    if it_session.env_type == EnvironmentType.SIM.name:
        # corsica sim环境不支持host reset,fio发流
        blkpf_multidev_io(it_session, dev_type, dev_queue_type)

    elif it_session.env_type == EnvironmentType.EMU.name or \
            it_session.env_type == EnvironmentType.HYBRID.name or \
            it_session.env_type == EnvironmentType.CRB.name:

        # 1.全部设备发fio流
        blkpf_multidev_io(it_session, dev_type, dev_queue_type, False)

        # 2.执行Power reset操作（直接在本机上使用命令行重启）
        dev_util.reset_by_bmc(it_session)

        # 3.加载virtio_blk驱动.需要先关闭RC超时时间
        disable_rc_timeout(host_session)

        # 4.加载virtio_blk驱动
        load_driver(host_session, dev_type)

    else:
        raise ENVError("environment error")
    # host reset后进行fio流通测试


def blkpf_multidev_hotplug(it_session, dev_type, dev_queue_type):
    # 登录N2
    n2_session = it_session.get_n2_session()

    # 测试带流热拔插场景
    if it_session.env_type == EnvironmentType.SIM.name:
        # corsica sim环境不支持virtio-blk设备的热拔插
        pass
        blkpf_singledev_io(it_session, dev_type, dev_queue_type)
    elif it_session.env_type == EnvironmentType.EMU.name or \
            it_session.env_type == EnvironmentType.CRB.name:

        # 随机选择一个dev_list里面的设备进行fio发流
        blk_dev_dict = blkpf_singledev_io(it_session, dev_type, dev_queue_type)
        blk_dev = list(blk_dev_dict.keys())[0]
        dev_bdf = blk_dev_dict[blk_dev]

        # 不带流热拔virtio-blk设备
        dev_bdf, n2_xml_file_abs = blk_detach_dev_PX2(it_session, blk_dev, dev_bdf)

        # 热插virtio-blk设备
        dev_util.attach_dev(n2_session, n2_xml_file_abs)

        # 热拔插后，对相同设备进行fio流通测试
        blk_run_fio_by_dev_name(it_session, blk_dev)

    else:
        raise ENVError("environment error")


def blkpf_multidev_io_forcekill_vhost(it_session, dev_type, dev_queue_type):
    n2_session = it_session.get_n2_session()
    host_session = it_session.get_host_session()

    if it_session.env_type == EnvironmentType.SIM.name:
        # corsica sim环境不支持vhost进程重启

        blkpf_multidev_io(it_session, dev_type, dev_queue_type)

    elif it_session.env_type == EnvironmentType.EMU.name or \
            it_session.env_type == EnvironmentType.CRB.name:
        # 1. 所有设备跑起来持续的fio流
        blkpf_multidev_io(it_session, dev_type, dev_queue_type, False)

        # 2.fio发流过程中，kill -9 vhost进程，并在N2侧确认vhost进程是否杀掉
        storage_util.kill_vhost(n2_session)

        # 3.N2端执行启动vhost进程脚本，再次启动vhost进程，判断vhost进程是否启动成功,实时获取vhost日志是否生成8个设备
        storage_util.start_vhost(n2_session, dev_type, 8)

        # 4.检查N2端设备是否driver_ok
        check_blk_dev_driver_ok(n2_session, dev_type, dev_queue_type)

        # 5.检查host端8个设备是否ok ，目前设备少了两个，暂时为6个
        check_host_blk_dev('host', host_session, 6)

        # 6. 查看fio发流是否已恢复
        storage_util.get_real_time_result_of_fio(host_session)

        # 7.杀掉fio发流
        storage_util.kill_fio_process(host_session)

        # 8.查询fio发流结果
        storage_util.get_final_result_of_fio(host_session)

    else:
        raise ENVError("environment error")


def get_random_blkdev(virtio_disks):
    # 随机选择一个字典并获取其 dev_name 值
    if virtio_disks:
        random_disks = random.choice(virtio_disks)
        dev_name = random_disks.get('target_dev')
        if not dev_name:
            logging.error("dev_name isn\'t found.")
        return random_disks

    else:
        logging.error("virtio_disks is None")
        raise TYPEError("virtio_disks is None")


def gen_blk_xml(disk):
    root = ET.Element("disk")
    root.set("type", disk['type'])
    root.set("device", disk['device'])
    root.set("model", disk['model'])
    driver = ET.SubElement(root, "driver")
    driver.set("name", disk['driver_name'])
    driver.set("type", disk['driver_type'])
    driver.set("queues", disk['driver_queues'])
    source = ET.SubElement(root, "source")
    source.set("type", "unix")
    source.set("path", disk['source_path'])
    reconnect = ET.SubElement(source, "reconnect")
    reconnect.set("enabled", "yes")
    reconnect.set("timeout", "10")
    target = ET.SubElement(root, "target")
    target.set("dev", disk['target_dev'])
    target.set("bus", disk['target_bus'])
    tree = ET.ElementTree(root)
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    dev = disk['target_dev']
    xml_file = f'blk_{dev}.xml'
    xml_file_abs = f'{parent_dir}/../../tmp/{xml_file}'
    tree.write(xml_file_abs)
    return xml_file


Jmnd_file_name = "/usr/share/jmnd/single/debug_script/2net_2blk/easy_bm.xml"
Jmnd_file_name_PX2 = "/usr/share/jmnd/single/debug_script/8net_8blk/easy_bm.xml"


def blk_detach_dev_PX2(it_session, blk_bdv, bdf=None):
    n2_session = it_session.get_n2_session()
    # file_name = download_file_from_n2(it_session, Jmnd_file_name_PX2)
    # domain_parser = EasyBmParser(file_name)
    # disks = domain_parser.get_disks() # disk xml文件内元素的字典
    disk_xml_file = DiskXMLGenerator.create_disk_xml(blk_bdv)
    # logging.info(f"\n----------------------------easy_bm.xml:disks:\n {disks}")
    selected_disk = {}

    # for disk in disks:
    #     if disk['target_dev'] == blk_bdv:
    #         selected_disk = disk
    #         break

    # 创建待拔插设备的xml文件，拷贝到N2，拷贝完成后删除本地的xml文件
    # xml_file = gen_blk_xml(selected_disk)

    scp_file_to_n2(it_session, disk_xml_file)
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    xml_file_abs = f'{parent_dir}/../../tmp/{disk_xml_file}'
    os.remove(xml_file_abs)
    n2_xml_file_abs = f'/root/{disk_xml_file}'
    dev_util.detach_dev(n2_session, n2_xml_file_abs)
    return bdf, n2_xml_file_abs


def blk_detach_dev(it_session, bdf=None):
    n2_session = it_session.get_n2_session()
    host_session = it_session.get_host_session()

    dev_list = dev_util.get_dev_list(n2_session)
    file_name = download_file_from_n2(it_session, Jmnd_file_name)
    domain_parser = EasyBmParser(file_name)
    disks = domain_parser.get_disks()
    logging.info(f"\n-----------------------------disks:\n {disks}")
    selected_disk = {}
    selected_bdf = ''
    if bdf is None:
        selected_disk = get_random_blkdev(disks)
        logging.info(f"\n-----------------------------selected_disk:\n {selected_disk}")
        # 获取选中设备的bdf号
        for dev in dev_list:
            if dev['dev_name'] == selected_disk['target_dev']:
                selected_bdf = dev['bdf']
                break
        logging.info(f"\n-----------------------------selected_bdf:\n {selected_bdf}")
    else:
        for dev in dev_list:
            if dev['bdf'] == bdf:
                selected_bdf = dev['bdf']
                for disk in disks:
                    if disk['target_dev'] == dev['dev_name']:
                        selected_disk = disk
                        break
                break
    # 创建待拔插设备的xml文件，拷贝到N2，拷贝完成后删除本地的xml文件
    xml_file = gen_blk_xml(selected_disk)
    scp_file_to_n2(it_session, xml_file)
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    xml_file_abs = f'{parent_dir}/../../tmp/{xml_file}'
    os.remove(xml_file_abs)
    n2_xml_file_abs = f'/root/{xml_file}'
    dev_util.detach_dev(n2_session, n2_xml_file_abs)
    return selected_bdf, n2_xml_file_abs
