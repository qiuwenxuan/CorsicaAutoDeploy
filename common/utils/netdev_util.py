import logging
import random
import re
import time

from common.Object.ItestObject import EnvironmentType
from common.Object.TrexSendConf import TrexSendConf, TrexInPort, TrexOutPort
from common.utils import session_util, dev_util, storage_util, trex_util
from common.utils import ovs_flow
from common.utils.easy_bm_parser import EasyBmParser
from common.utils.exception import GetNetworkInterfaceError, Error
from common.utils.ovs_result_parser import OVSPortParser
from common.utils.trex_util import start_tcpdump, check_tcpdump_result, send_packet_on_trex_console
from common.utils.util import download_file_from_n2, subprocess_command

Jmnd_file_path = "/usr/share/jmnd/single/debug_script/2net_2blk"
Jmnd_file_name = "/usr/share/jmnd/single/debug_script/2net_2blk/easy_bm.xml"
src_ip = "185.233.190.2"


def get_host_netdev(host_name, host_session):
    # 1. 执行”ll /sys/class/net“ 命令
    cmd = f'ls -l  /sys/class/net'
    result = host_session.execute_command(cmd)
    logging.info(f"\n execute_command({cmd}):\n {result}")
    # 2. 解析 netdev
    virtio_interfaces = []
    net_lines = result.strip().split('\n')
    for line in net_lines:
        # 在 Virtio 网卡的设备名通常以 "v" 或 "virtio" 开头
        if 'virtio' in line:
            parts = line.split('/')
            if len(parts) >= 4:
                netdev = {}
                netdev['host_name'] = host_name
                netdev['dev_name'] = parts[-1]
                netdev['pcie_num'] = parts[4]

                # # 获取mac 地址
                # mac_command = f"cat /sys/class/net/{netdev['dev_name']}/address"
                # result = host_session.execute_command(mac_command)
                # mac_addr = result.strip()
                # netdev['mac_addr'] = mac_addr

                # 获取mac地址和IP  ip addr show dev_neme
                mac_command = f"ip addr show {netdev['dev_name']}"
                output = host_session.execute_command(mac_command)
                result = output.strip()
                logging.info(f"------------result:{result}")
                mac_match = re.search(r'link/ether ([\w:]+)', result)
                ipv4_match = re.search(r'inet ([\d.]+)/\d+', result)
                if mac_match:
                    netdev['mac_addr'] = mac_match.group(1)
                if ipv4_match:
                    netdev['ip_v4'] = ipv4_match.group(1)

                virtio_interfaces.append(netdev)
    logging.info(f"virtio_interfaces:{virtio_interfaces}")
    if virtio_interfaces is None:
        logging.error(f"virtio_interfaces is None")
        raise GetNetworkInterfaceError("get virtio_interfaces error")

    return virtio_interfaces


def get_random_two_netdevs(virtio_interfaces):
    # 随机选择两个网卡
    if virtio_interfaces:
        if len(virtio_interfaces) >= 2:
            random_interfaces = random.sample(virtio_interfaces, 2)
        else:
            random_interfaces = virtio_interfaces
        return random_interfaces
    else:
        logging.error("virtio_interfaces is None")
        raise Error("virtio_interfaces is None")


def set_interfaces_ip_and_check(host_session, dev_name, ip):
    config_cmd = f'ifconfig {dev_name} {ip}/24'
    host_session.execute_command(config_cmd)
    # check ip
    grep_cmd = r"grep -Eo 'inet ([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})' | awk '{print $2}'"
    check_cmd = f"ifconfig {dev_name} | {grep_cmd}"
    result = host_session.execute_command(check_cmd)
    logging.info(f"execute command:ifconfig: result:{result}")
    ip_address = result.strip()
    if ip_address == ip:
        return True
    else:
        return False


def ping_test_host_to_host(host_session, target_ip):
    cmd = f"ping -c 4 {target_ip}"
    ping_output = host_session.execute_command(cmd)
    result = ping_output.strip()
    logging.info(f"Ping test result is {result}")
    if re.search(r"(\d+) packets transmitted, (\d+) received", result):
        logging.info(f"Ping test success")
        return True
    else:
        logging.info(f"Ping test failed")
        return False


def get_netdev_source_path(it_session, netdev, Jmnd_file_name=Jmnd_file_name):
    file_name = download_file_from_n2(it_session, Jmnd_file_name)
    domain_parser = EasyBmParser(file_name)
    interfaces = domain_parser.get_interfaces()
    source_path = None
    for interface in interfaces:
        if netdev['mac_addr'] == interface['mac_address']:
            netdev['source_path'] = interface['source_path']
            source_path = interface['source_path']
            break

    return source_path


def get_ovs_port_from_netdev(it_session, netdev):
    # 1. 根据netdev[mac_address]与easy_bm中interface 的mac_address 一一对应关系得到interface的source_path
    source_path = get_netdev_source_path(it_session, netdev, Jmnd_file_name)
    # 2. 执行ovs-vsctl  show获取devnet 信息
    cmd = 'ovs-vsctl  show'
    n2_session = it_session.get_n2_session()
    ovs_show_output = n2_session.execute_command(cmd)
    parser = OVSPortParser(ovs_show_output)
    parser.parse()
    # logging.info(f"-----------------------------" + parser.print_ports())
    for ovs_port in parser.ports:
        if ovs_port.port_type == 'dpdk' and 'iface' in ovs_port.options \
                and source_path == ovs_port.options['iface']:
            netdev['ovs_uptap'] = ovs_port.interface_name
            netdev['ovs_queues'] = ovs_port.options['queues']
            break
    return netdev


# def random_get_virtio_two_netdev(it_session,host_virtio_interfaces):
#     host_session = it_session.get_host_session()
#     host_virtio_interfaces = get_host_netdev("host", host_session)
#     logging.info(f"virtio_interfaces:{host_virtio_interfaces}")
#     assert host_virtio_interfaces
#     return get_random_two_netdevs(host_virtio_interfaces)


# second_host_virtio_interfaces = get_host_netdev("h2", second_host_session)
# logging.info(f"virtio_interfaces:{second_host_virtio_interfaces}")
# assert second_host_virtio_interfaces
# h2_v_interface = get_random_two_netdevs(second_host_virtio_interfaces)
# return host_v_interface, h2_v_interface


def get_net_qp(session, port):
    """
    获取指定网口的qp最大值及当前值
    """
    cmd = f'ethtool -l {port}'
    result = session.execute_command(cmd)
    combined_values = re.findall(r'Combined:\s+(\d+)', result)
    return combined_values


def modify_net_qp(session, port, value):
    """
    修改指定网口的qp当前值
    """
    cmd = f'ethtool -L {port} combined {value}'
    session.execute_command(cmd)
    combined_values = get_net_qp(session, port)
    logging.info(f"combined_values[1]:{combined_values[1]}")
    if int(combined_values[1]) != value:
        raise Exception('错误：网口的qp值未设置成功！')


# def set_trex_config_before_send_packets(it_session, type, dev_queue_type,ovsqueues=False):
# #     host_session = it_session.get_host_session()
# #     n2_session = it_session.get_n2_session()
# #     # 1. 获取virtio 网络设备名称以及IP
# #     interface1, interface2 = get_test_netdev_SIM(it_session, dev_queue_type)
# #     import pdb
# #     pdb.set_trace()
# #     # get ovs port
# #     interface_path_1 = get_ovs_port_from_netdev(it_session, interface1)
# #     interface_path_2 = get_ovs_port_from_netdev(it_session, interface2)
# #     host_v_interface1 = interface_path_1['dev_name']
# #     host_v_interface2 = interface_path_2['dev_name']
# #     host_v_interface1_ovsport = interface_path_1['ovs_uptap']
# #     host_v_interface1_ovsqueues = interface_path_1['ovs_queues']
# #     host_v_interface2_ovsport = interface_path_2['ovs_uptap']
# #     src = "185.233.190.2"
# #     # 随机获取macport口
# #     macport_interface1, macport_interface2 = sim_random_get_macport(2)
# #     macport_interface1_dev_name = macport_interface1['dev_name']
# #     macport_interface1_ovsport = macport_interface1['ovs_uptap']
# #     macport_interface2_dev_name = macport_interface2['dev_name']
# #
# #     if type == 'host_host':
# #         ovs_inport = host_v_interface1_ovsport
# #         ovs_output = host_v_interface2_ovsport
# #         trex_session_type = "host"
# #         trex_session = host_session
# #         trex_port1 = host_v_interface1
# #         trex_port2 = host_v_interface2
# #         tcpdump_session = host_session
# #         tcpdump_port = host_v_interface2
# #     elif type == 'host_uplink':
# #         ovs_inport = host_v_interface1_ovsport
# #         ovs_output = macport_interface1_ovsport
# #         trex_session_type = "host"
# #         trex_session = host_session
# #         trex_port1 = host_v_interface1
# #         trex_port2 = host_v_interface2
# #         tcpdump_session = n2_session
# #         tcpdump_port = macport_interface1_dev_name
# #     elif type == 'uplink_host':
# #         ovs_inport = macport_interface1_ovsport
# #         ovs_output = host_v_interface1_ovsport
# #         trex_session_type = "n2"
# #         trex_session = n2_session
# #         trex_port1 = macport_interface1_dev_name
# #         trex_port2 = macport_interface2_dev_name
# #         tcpdump_session = host_session
# #         tcpdump_port = host_v_interface1
# #     else:
# #         raise Exception('错误：输入的类型有误！')
#
#     # 配置流表
#     ovs_flow.del_flows(n2_session)
#     ovs_flow.add_flows(n2_session, ovs_inport, src, ovs_output)
#     # 拷贝trex_cfg.yaml文件到trex运行环境，并修改配置
#     trex_util.scp_trex_cfg_yaml_to_trex_server(it_session, trex_session_type)
#     trex_util.config_trex_cfg_yaml_on_trex_server(trex_session, trex_port1, trex_port2)
#     # 在trex运行环境上先后启动trex-server及trex-console
#     trex_util.start_trex_server(trex_session)
#     trex_util.start_trex_console(trex_session)
#     if ovsqueues:
#         return tcpdump_session, tcpdump_port, trex_session, src, ovs_inport, ovs_output, host_v_interface1_ovsqueues
#     else:
#         return tcpdump_session, tcpdump_port, trex_session, src, ovs_inport, ovs_output

def get_test_netdev_SIM(it_session, dev_queue_type):
    pass


def netpf_multidev_host_host(it_session, dev_type, dev_queue_type):
    # 0.pre 登录前后端成功,确认host端加载驱动成功
    n2_session, host_session = session_util.pretest(it_session, dev_type)
    src_ip = "185.233.190.2"
    if it_session.env_type == EnvironmentType.SIM.name:
        interface1, interface2 = get_test_host_ens(it_session, dev_type, dev_queue_type)
        # macport_interface1, macport_interface2 = sim_random_get_macport(2)
        # 配置Trex

        trex_inport = TrexInPort(interface1['dev_name'], 'host', interface1['ovs_uptap'], src_ip)
        trex_outport = TrexOutPort(interface2['dev_name'], 'host', interface2['ovs_uptap'])
        trexSendConf = TrexSendConf(trex_inport, trex_outport)

        # 配置流表
        config_ovs_flow(n2_session, trex_inport, trex_outport)

        prepare_for_sent_trex_package(it_session, trexSendConf)

        trex_send_one_packet_and_check_from_host(it_session, trexSendConf)

    elif it_session.env_type == EnvironmentType.EMU.name or \
            it_session.env_type == EnvironmentType.CRB.name:
        pass
    elif it_session.env_type == EnvironmentType.HYBRID.name:
        pass
    else:
        raise TypeError(f"it_session.env_type error.it_session.env_type={it_session.env_type}")


# def netpf_multidev_net_hyper_commander_reconnect(it_session, dev_type, dev_queue_type):
#     # 0.pre 登录前后端成功,确认host端加载驱动成功
#     n2_session, host_session = session_util.pretest(it_session, dev_type)
#     if it_session.env_type == EnvironmentType.SIM.name:
#         tcpdump_session, tcpdump_port, trex_session, src, ovs_inport, ovs_output = trex_config_before_send_packets(
#             it_session, 'uplink_host')
#         # trex发一个包并检测是否收到
#         trex_util.trex_send_one_packet_and_check(tcpdump_session, tcpdump_port, trex_session, src, n2_session,
#                                                  ovs_inport, ovs_output, 1)
#         # 再发一个包验证offload
#         trex_util.trex_send_one_packet_and_check(tcpdump_session, tcpdump_port, trex_session, src, n2_session,
#                                                  ovs_inport, ovs_output, 2)
#         # 在N2上ovs断链重连（SIM环境暂不支持该功能）
#         pass
#         logging.info(f'SIM环境暂不支持ovs断链重连的功能')
#         # 配置流表
#         ovs_flow.del_flows(n2_session)
#         ovs_flow.add_flows(n2_session, ovs_inport, src, ovs_output)
#         # trex发一个包并检测是否收到
#         trex_util.trex_send_one_packet_and_check(tcpdump_session, tcpdump_port, trex_session, src, n2_session,
#                                                  ovs_inport, ovs_output, 1)
#         # 再发一个包验证offload
#         trex_util.trex_send_one_packet_and_check(tcpdump_session, tcpdump_port, trex_session, src, n2_session,
#                                                  ovs_inport, ovs_output, 2)
#         # 在N2上hyper-commander断链重连（SIM环境暂不支持该功能）
#         pass
#         logging.info(f'SIM环境暂不支持hyper-commander断链重连的功能')
#         # 配置流表
#         ovs_flow.del_flows(n2_session)
#         ovs_flow.add_flows(n2_session, ovs_inport, src, ovs_output)
#         # trex发一个包并检测是否收到
#         trex_util.trex_send_one_packet_and_check(tcpdump_session, tcpdump_port, trex_session, src, n2_session,
#                                                  ovs_inport, ovs_output, 1)
#         # 再发一个包验证offload
#         trex_util.trex_send_one_packet_and_check(tcpdump_session, tcpdump_port, trex_session, src, n2_session,
#                                                  ovs_inport, ovs_output, 2)
#     elif it_session.env_type == EnvironmentType.EMU.name:
#         pass
#     elif it_session.env_type == EnvironmentType.HYBRID.name:
#         pass
#     else:
#         raise TypeError(f"it_session.env_type error.it_session.env_type={it_session.env_type}")

def low_speed_path_test(it_session, trexSendConf, timeout=30):
    n2_session = it_session.get_n2_session()
    # 1.N2端配置流表
    ret = config_ovs_flow(n2_session, trexSendConf)
    assert ret
    logging.info(f"1.N2端配置流表 成功")

    # 2.配置trex
    ret = config_trex(it_session, trexSendConf)
    assert ret
    logging.info(f"2.配置trex 成功")

    # 3.trex 发流前准备
    #   1)启动trex-server
    #   2)启动trex-console 准备发流
    #   2)启动tcpdump 准备抓包
    ret = prepare_for_sent_trex_package(it_session, trexSendConf, timeout)
    assert ret
    logging.info(f"3.trex 发流前准备 成功")

    # 4 发流：在trex-console 里发第一个包成功
    ret = trex_send_packet(it_session, trexSendConf)
    assert ret
    logging.info(f"4 发流：在trex-console 里发第一个包成功 成功")
    # 5. 检查第一个包的正确性
    ret = check_the_first_packet(it_session, trexSendConf)
    assert ret
    logging.info(f"5. 检查第一个包的正确性 成功")
    return True


def offload_path_test(it_session, trexSendConf):
    """
    功能：快速路径测试
    """
    # 4 发流：在trex-console 里再发1个包（第二个包）
    ret = trex_send_packet(it_session, trexSendConf)
    assert ret
    logging.info(f"4 发流：在trex-console 里发第二个包成功 成功")
    # 5. 检查第二个包的正确性
    ret = check_packet(it_session, trexSendConf, 2)
    assert ret
    logging.info(f"5. 检查第一个包的正确性 成功")
    return True


def netpfdev_host_host_lsp(it_session, dev_type: str, dev_queue_type: str):
    """
    功能：测试慢速路径流通(host-host)。

    参数：
    it_session: IT会话对象，集成测试会话。
    dev_type: 前端设备类型，‘net|blk|nvme’的其中一种。
    dev_queue_type:  后端队列类型，'Legacy|Modern|Packed'的其中一种。

    返回：
    函数没有明确返回值，但可能会通过it_session对设备进行
    示例：
    调用 netpfdev_host_host_lsp(session, 'net', 'Legacy') 测试Legacy网络设备的HostToUplin慢速路径流通。
    """

    # 0.1 pre 登录前后端成功,确认host端加载驱动成功
    n2_session, host_session = session_util.pretest(it_session, dev_type)
    src_ip = "185.233.190.2"
    if it_session.env_type == EnvironmentType.SIM.name:
        # 1. 获取host端测试的两个ens端口
        interface1, interface2 = get_test_host_ens(it_session, dev_type, dev_queue_type)
        # 取出列表的第一个元素 sim_random_get_macport = 'dev_name': f'macif{i}', 'ovs_tap': f'vnet{i}'
        # macport_interface = sim_random_get_macport(1)[0]

        # 2. 配置Trex发流
        trex_inport = TrexInPort(interface1['dev_name'], 'host', interface1['ovs_uptap'], src_ip)
        trex_outport = TrexOutPort(interface2['dev_name'], 'host', interface2['ovs_uptap'])
        trexSendConf = TrexSendConf(trex_inport, trex_outport)

        # 3. 慢速路径发流
        ret = low_speed_path_test(it_session, trexSendConf)
        assert ret

    elif it_session.env_type == EnvironmentType.EMU.name or \
            it_session.env_type == EnvironmentType.CRB.name:
        interface1, interface2 = get_test_host_ens(it_session, dev_type, dev_queue_type)

        # 配置Trex输入端口和输出端口
        trex_inport = TrexInPort(interface1['dev_name'], 'host', interface1['ovs_uptap'], src_ip)
        trex_outport = TrexOutPort(interface2['dev_name'], 'host', interface2['ovs_uptap'])
        # 配置发流端口
        trexSendConf = TrexSendConf(trex_inport, trex_outport)

        ret = low_speed_path_test(it_session, trexSendConf, 600)
        assert ret
    elif it_session.env_type == EnvironmentType.HYBRID.name:
        pass
    else:
        raise TypeError(f"it_session.env_type error.it_session.env_type={it_session.env_type}")


def netpfdev_host_uplink_lsp(it_session, dev_type: str, dev_queue_type: str):
    """
    功能：测试慢速路径流通(host-uplink)。

    参数：
    it_session: IT会话对象，集成测试会话。
    dev_type: 前端设备类型，‘net|blk|nvme’的其中一种。
    dev_queue_type:  后端队列类型，'Legacy|Modern|Packed'的其中一种。

    返回：
    函数没有明确返回值，但可能会通过it_session对设备进行
    示例：
    调用 netpfdev_host_uplink_lsp(session, 'net', 'Legacy') 测试Legacy网络设备的HostToUplin慢速路径流通。
    """

    # 0.1 pre 登录前后端成功,确认host端加载驱动成功
    n2_session, host_session = session_util.pretest(it_session, dev_type)
    src_ip = "185.233.190.2"
    if it_session.env_type == EnvironmentType.SIM.name:
        # 0.1 获取测试的两个端口
        interface1, interface2 = get_test_host_ens(it_session, dev_type, dev_queue_type)
        # 取出列表的第一个元素
        macport_interface = sim_random_get_macport(1)[0]
        # 配置Trex
        trex_inport = TrexInPort(interface1['dev_name'], 'host', interface1['ovs_uptap'], src_ip)
        trex_outport = TrexOutPort(macport_interface['dev_name'], 'N2', macport_interface['ovs_tap'])
        trexSendConf = TrexSendConf(trex_inport, trex_outport)

        ret = low_speed_path_test(it_session, trexSendConf)
        assert ret

    elif it_session.env_type == EnvironmentType.EMU.name or \
            it_session.env_type == EnvironmentType.CRB.name:
        pass
    elif it_session.env_type == EnvironmentType.HYBRID.name:
        pass
    else:
        raise TypeError(f"it_session.env_type error.it_session.env_type={it_session.env_type}")


def netpf_multidev_uplink_host_offload(it_session, dev_type: str, dev_queue_type: str):
    """
        功能：测试快慢速路径叠加流通(uplink-host & uplink-host offload)。

        参数：
        it_session: IT会话对象，集成测试会话。
        dev_type: 前端设备类型，‘net|blk|nvme’的其中一种。
        dev_queue_type:  后端队列类型，'Legacy|Modern|Packed'的其中一种。

        返回：
        函数没有明确返回值，但可能会通过it_session对设备进行
        示例：
        调用 netpfdev_host_uplink_lsp(session, 'net', 'Legacy') 测试Legacy网络设备的HostToUplin慢速路径流通。
    """
    # 0.1 pre 登录前后端成功,确认host端加载驱动成功
    src_ip = "185.233.190.2"
    if it_session.env_type == EnvironmentType.SIM.name:
        # 0.1 获取测试的两个端口
        interface1, interface2 = get_test_host_ens(it_session, dev_type, dev_queue_type)
        # 取出列表的第一个元素
        macport_interface = sim_random_get_macport(1)[0]
        # 配置Trex
        trex_inport = TrexInPort(macport_interface['dev_name'], 'N2', macport_interface['ovs_tap'], src_ip)
        trex_outport = TrexOutPort(interface1['dev_name'], 'host', interface1['ovs_uptap'])
        trexSendConf = TrexSendConf(trex_inport, trex_outport)

        ret = low_speed_path_test(it_session, trexSendConf)
        assert ret

        ret = offload_path_test(it_session, trexSendConf)
        assert ret
    elif it_session.env_type == EnvironmentType.EMU.name or \
            it_session.env_type == EnvironmentType.CRB.name:
        pass
    elif it_session.env_type == EnvironmentType.HYBRID.name:
        pass
    else:
        raise TypeError(f"it_session.env_type error.it_session.env_type={it_session.env_type}")


def get_trexSendConf_host_host(it_session, dev_type, dev_queue_type):
    # 0.1 获取测试的两个端口
    interface1, interface2 = get_test_host_ens(it_session, dev_type, dev_queue_type)
    # 配置Trex
    trex_inport = TrexInPort(interface1['dev_name'], 'host', interface1['ovs_uptap'], src_ip)
    trex_outport = TrexOutPort(interface2['dev_name'], 'host', interface2['ovs_uptap'])
    trexSendConf = TrexSendConf(trex_inport, trex_outport)
    return trexSendConf


def get_trexSendConf_host_uplink(it_session, dev_type, dev_queue_type):
    # 0.1 获取测试的两个端口
    interface1, interface2 = get_test_host_ens(it_session, dev_type, dev_queue_type)
    # 取出列表的第一个元素
    macport_interface = sim_random_get_macport(1)[0]
    # 配置Trex
    trex_inport = TrexInPort(interface1['dev_name'], 'host', interface1['ovs_uptap'], src_ip)
    trex_outport = TrexOutPort(macport_interface['dev_name'], 'N2', macport_interface['ovs_tap'])
    trexSendConf = TrexSendConf(trex_inport, trex_outport)
    return trexSendConf


def get_trexSendConf_uplink_host(it_session, dev_type, dev_queue_type):
    # 0.1 获取测试的两个端口
    interface1, interface2 = get_test_host_ens(it_session, dev_type, dev_queue_type)
    # 取出列表的第一个元素
    macport_interface = sim_random_get_macport(1)[0]
    # 配置Trex
    trex_inport = TrexInPort(macport_interface['dev_name'], 'N2', macport_interface['ovs_tap'], src_ip)
    trex_outport = TrexOutPort(interface1['dev_name'], 'host', interface1['ovs_uptap'])
    trexSendConf = TrexSendConf(trex_inport, trex_outport)
    return trexSendConf


def netpf_multidev_ctrlqueue_modify_qp_uplink_host(it_session, dev_type: str, dev_queue_type: str):
    """
        功能：测试net legacy多设备多队列ctrlqueue反复修改active qp(uplink-host)。

        参数：
        it_session: IT会话对象，集成测试会话。
        dev_type: 前端设备类型，‘net|blk|nvme’的其中一种。
        dev_queue_type:  后端队列类型，'Legacy|Modern|Packed'的其中一种。

        返回：
        函数没有明确返回值，但可能会通过it_session对设备进行
        示例：
        调用 netpf_multidev_ctrlqueue_modify_qp_uplink_host(session, 'net', 'Legacy') 测试Legacy网络设备的修改qp慢速路径流通。
    """
    src_ip = "185.233.190.2"
    if it_session.env_type == EnvironmentType.SIM.name:
        # 0.1 获取测试的两个端口
        interface1, interface2 = get_test_host_ens(it_session, dev_type, dev_queue_type)
        # 取出列表的第一个元素
        macport_interface = sim_random_get_macport(1)[0]
        # 配置Trex
        trex_inport = TrexInPort(macport_interface['dev_name'], 'N2', macport_interface['ovs_tap'], src_ip)
        trex_outport = TrexOutPort(interface1['dev_name'], 'host', interface1['ovs_uptap'])
        trexSendConf = TrexSendConf(trex_inport, trex_outport)

        ret = low_speed_path_test(it_session, trexSendConf)
        assert ret

        # 获取网口设备的qp最大值及当前值，应与N2侧配置的值相等
        host_session = it_session.get_host_session()
        qp_values = get_net_qp(host_session, interface1['dev_name'])
        if qp_values[0] == qp_values[1] == interface1['ovs_queues']:
            logging.info(f"qp最大值'{qp_values[0]}'=qp当前值'{qp_values[1]}'=N2侧配置的值'{interface1['ovs_queues']}'")
        else:
            raise Exception('错误：qp最大值、qp当前值、N2侧配置的值，三者不相等')
        # 修改qp当前值后，查看收包是否正常
        for i in range(1, 11):
            logging.info(f"--------------------这是第{i}次循环------------------------")
            modify_net_qp(host_session, interface1['dev_name'], random.randint(1, int(interface1['ovs_queues'])))
            # trex发一个包并检测是否收到
            ret = low_speed_path_test(it_session, trexSendConf)
            assert ret
        modify_net_qp(host_session, interface1['dev_name'], int(interface1['ovs_queues']))
    elif it_session.env_type == EnvironmentType.EMU.name or \
            it_session.env_type == EnvironmentType.CRB.name:
        # 发流前准备
        interface = emu_net_prepare(it_session, dev_queue_type)
        ensX = interface['dev_name']
        netX = interface['ovs_uptap']
        try:
            host_session = it_session.get_host_session()
            # get qp_values
            qp_values = get_host_qp_and_n2_qp_value(it_session, ensX, netX)
            # check host maximum qp num = current qp num = n2 qp num
            assert len(qp_values) == 3 and qp_values[0] == qp_values[1] and qp_values[2] is not None and qp_values[0] == \
                   qp_values[2], 'host侧查询ensX设备的qp最大值及当前值，与N2侧设置的vnet的qp值不相等！'
            # modify qp num repeatedly
            # 修改qp当前值后，查看收包是否正常
            for i in range(1, 11):
                logging.info(f"--------------------这是第{i}次循环------------------------")
                modify_net_qp(host_session, ensX, random.randint(1, int(qp_values[2])))
                is_success = ping_test_0_loss_rate(host_session, '7.7.7.7')
                assert is_success
        finally:
            emu_net_teardown(it_session, ensX)

    elif it_session.env_type == EnvironmentType.HYBRID.name:
        pass
    else:
        raise TypeError(f"it_session.env_type error.it_session.env_type={it_session.env_type}")


def netpf_multidev_reload_driver_host_uplink(it_session, dev_type, dev_queue_type):
    """
            功能：net-legacy-host反复加载卸载virtio_net驱动，慢速路径流通(host-uplink)

            参数：
            it_session: IT会话对象，集成测试会话。
            dev_type: 前端设备类型，‘net|blk|nvme’的其中一种。
            dev_queue_type:  后端队列类型，'Legacy|Modern|Packed'的其中一种。

            返回：
            函数没有明确返回值，但可能会通过it_session对设备进行
            示例：
            调用 netpf_multidev_reload_driver_host_uplink(session, 'net', 'Legacy') 测试Legacy网络设备的HostToUplin慢速路径流通。
        """
    # 0.pre 登录前后端成功,确认host端加载驱动成功
    n2_session, host_session = session_util.pretest(it_session, dev_type)
    src_ip = "185.233.190.2"
    if it_session.env_type == EnvironmentType.SIM.name:
        # 获取trexSendConf的配置
        trexSendConf = get_trexSendConf_host_uplink(it_session, dev_type, dev_queue_type)
        ret = low_speed_path_test(it_session, trexSendConf)
        assert ret

        for i in range(1, 11):
            logging.info(f"--------------------这是第{i}次循环------------------------")
            # host侧执行驱动卸载后再加载，（SIM环境暂不支持驱动卸载加载的功能）
            pass
            logging.info(f'SIM环境暂不支持驱动卸载加载的功能')
            # 配置流表
            ret = low_speed_path_test(it_session, trexSendConf)
            assert ret

    elif it_session.env_type == EnvironmentType.EMU.name or \
            it_session.env_type == EnvironmentType.CRB.name:
        # 准备工作
        interface = emu_net_prepare(it_session, dev_queue_type)
        ensX = interface['dev_name']
        try:
            for i in range(3):  # 重复执行50次
                logging.info(f"--------------------这是第{i + 1}次循环------------------------")
                # ping 10 个包
                result = host_session.execute_command(
                    "ping 7.7.7.7 -c 1|grep loss|awk '{print $6}'|awk -F \"%\" '{print $1}'").strip()
                logging.info(f'--------------------------------ping result is: {result}')
                # 查看丢包百分比
                assert result == '0'
                logging.info('---------------正在持续ping包')
                # 持续ping包
                host_session.execute_command("tmux new-window -n MyWindow 'ping 7.7.7.7'")
                logging.info('---------------------正在卸载virtio_net驱动')
                # 卸载virtio_net驱动
                dev_util.unload_driver(host_session, dev_type)
                # ping 1 个包
                result = host_session.execute_command(
                    "ping 7.7.7.7 -c 1|grep loss|awk '{print $6}'|awk -F \"%\" '{print $1}'").strip()
                logging.info(f'--------------------------------ping result is: {result}')
                # 查看丢包百分比
                assert result == '100'
                logging.info('---------------------正在加载virtio_net驱动')
                # host侧加载virtio_net驱动
                dev_util.load_driver(host_session, dev_type)
                # 重新准备host端的资源
                emu_net_prepare(it_session, dev_queue_type, host_reprepare_only=True)
                # host kill ping
                host_session.execute_command('tmux kill-window -t MyWindow')
        finally:
            emu_net_teardown(it_session, ensX)

    elif it_session.env_type == EnvironmentType.HYBRID.name:
        pass
    else:
        raise TypeError(f"it_session.env_type error.it_session.env_type={it_session.env_type}")


def netpf_multidev_uplink_host_lsp(it_session, dev_type: str, dev_queue_type: str):
    """
    功能：测试慢速路径流通(host-uplink)。

    参数：
    it_session: IT会话对象，集成测试会话。
    dev_type: 前端设备类型，‘net|blk|nvme’的其中一种。
    dev_queue_type:  后端队列类型，'Legacy|Modern|Packed'的其中一种。

    返回：
    函数没有明确返回值，但可能会通过it_session对设备进行
    示例：
    调用 netpfdev_host_uplink_lsp(session, 'net', 'Legacy') 测试Legacy网络设备的HostToUplin慢速路径流通。
    """

    # 0.1 pre 登录前后端成功,确认host端加载驱动成功
    src_ip = "185.233.190.2"
    if it_session.env_type == EnvironmentType.SIM.name:
        # 0.1 获取测试的两个端口
        interface1, interface2 = get_test_host_ens(it_session, dev_type, dev_queue_type)
        # 取出列表的第一个元素
        macport_interface = sim_random_get_macport(1)[0]
        # 配置Trex
        trex_inport = TrexInPort(macport_interface['dev_name'], 'N2', macport_interface['ovs_tap'], src_ip)
        trex_outport = TrexOutPort(interface1['dev_name'], 'host', interface1['ovs_uptap'])
        trexSendConf = TrexSendConf(trex_inport, trex_outport)

        ret = low_speed_path_test(it_session, trexSendConf)
        assert ret
    elif it_session.env_type == EnvironmentType.EMU.name or \
            it_session.env_type == EnvironmentType.CRB.name:
        pass
    elif it_session.env_type == EnvironmentType.HYBRID.name:
        pass
    else:
        raise TypeError(f"it_session.env_type error.it_session.env_type={it_session.env_type}")


def netpf_multidev_host_reset_uplink_host_and_offload(it_session, dev_type, dev_queue_type):
    """
        功能：host reset，加载virtio_net驱动，慢速路径流通(uplink-host & uplink-host offload)。

        参数：
        it_session: IT会话对象，集成测试会话。
        dev_type: 前端设备类型，‘net|blk|nvme’的其中一种。
        dev_queue_type:  后端队列类型，'Legacy|Modern|Packed'的其中一种。

        返回：
        函数没有明确返回值，但可能会通过it_session对设备进行
        示例：
        调用 netpf_multidev_host_reset_uplink_host_and_offload(session, 'net', 'Legacy')
             测试host reset，加载virtio_net驱动，Legacy网络设备的快速路径流通(uplink-host & uplink-host offload)。
        """
    # 0.pre 登录前后端成功,确认host端加载驱动成功
    n2_session, host_session = session_util.pretest(it_session, dev_type)
    src_ip = "185.233.190.2"
    if it_session.env_type == EnvironmentType.SIM.name:

        trexSendConf = get_trexSendConf_uplink_host(it_session, dev_type, dev_queue_type)

        ret = low_speed_path_test(it_session, trexSendConf)
        assert ret
        ret = offload_path_test(it_session, trexSendConf)
        assert ret

        # host reset，等待host启动成功，并确认已加载virtio_net驱动（SIM环境暂不支持host reset的功能）
        pass
        logging.info(f'SIM环境暂不支持host reset的功能')

        ret = low_speed_path_test(it_session, trexSendConf)
        assert ret
        # 再发一个包验证offload
        ret = offload_path_test(it_session, trexSendConf)
        assert ret
    elif it_session.env_type == EnvironmentType.EMU.name or \
            it_session.env_type == EnvironmentType.CRB.name:
        # 准备工作
        interface = emu_net_prepare(it_session, dev_queue_type)
        netX = interface['ovs_uptap']
        try:
            # ping 10 个包
            result = host_session.execute_command(
                "ping 7.7.7.7 -c 10|grep loss|awk '{print $6}'|awk -F \"%\" '{print $1}'").strip()
            # 查看丢包百分比
            assert result == '0'
            # net table count check
            m1 = ovs_flow.get_flow_packets_without_nw_src(n2_session, netX, 'dpdk0')
            assert m1 == 10
            m2 = ovs_flow.get_offload_flow_packets_without_nw_src(n2_session, netX, 'dpdk0')
            assert m2 == 9
            # host reset
            dev_util.reset_by_bmc(it_session)
            # disable RC timeout
            storage_util.disable_rc_timeout(host_session)
            # load virtio_net driver
            dev_util.load_driver(host_session, dev_type)
            # re-prepare
            ovs_flow.del_flows(n2_session)
            interface = emu_net_prepare(it_session, dev_queue_type, reprepare=True)
            netX = interface['ovs_uptap']
            # ping 10 个包
            result = host_session.execute_command(
                "ping 7.7.7.7 -c 10|grep loss|awk '{print $6}'|awk -F \"%\" '{print $1}'").strip()
            # 查看丢包百分比
            assert result == '0'
            # net table count check
            m1 = ovs_flow.get_flow_packets_without_nw_src(n2_session, netX, 'dpdk0')
            assert m1 == 10
            m2 = ovs_flow.get_offload_flow_packets_without_nw_src(n2_session, netX, 'dpdk0')
            assert m2 == 9
        finally:
            emu_net_teardown(it_session, ensX=interface['dev_name'])
    elif it_session.env_type == EnvironmentType.HYBRID.name:
        pass
    else:
        raise TypeError(f"it_session.env_type error.it_session.env_type={it_session.env_type}")


def netpf_multidev_hotplug_uplink_host_and_offload(it_session, dev_type, dev_queue_type):
    """
        功能：设备热插拔,快慢速路径流通(uplink-host & uplink-host offload)。

        参数：
        it_session: IT会话对象，集成测试会话。
        dev_type: 前端设备类型，‘net|blk|nvme’的其中一种。
        dev_queue_type:  后端队列类型，'Legacy|Modern|Packed'的其中一种。

        返回：
        函数没有明确返回值，但可能会通过it_session对设备进行
        示例：
        调用 netpf_multidev_hotplug_uplink_host_and_offload(session, 'net', 'Legacy')
             测试host reset，加载virtio_net驱动，Legacy网络设备的快速路径流通(uplink-host & uplink-host offload)。
    """
    # 0.pre 登录前后端成功,确认host端加载驱动成功
    n2_session, host_session = session_util.pretest(it_session, dev_type)
    if it_session.env_type == EnvironmentType.SIM.name:
        trexSendConf = get_trexSendConf_uplink_host(it_session, dev_type, dev_queue_type)

        ret = low_speed_path_test(it_session, trexSendConf)
        assert ret
        ret = offload_path_test(it_session, trexSendConf)
        assert ret
        # N2侧热拔net后并热插（SIM环境暂不支持该功能）
        pass
        logging.info(f'SIM环境暂不支持net热拔插的功能')

        ret = low_speed_path_test(it_session, trexSendConf)
        assert ret
        ret = offload_path_test(it_session, trexSendConf)
        assert ret
    elif it_session.env_type == EnvironmentType.EMU.name or \
            it_session.env_type == EnvironmentType.CRB.name:
        # 准备工作
        interface = emu_net_prepare(it_session, dev_queue_type)
        ensX = interface['dev_name']
        netX = interface['ovs_uptap']
        try:
            # ping 10 个包
            result = host_session.execute_command(
                "ping 7.7.7.7 -c 10|grep loss|awk '{print $6}'|awk -F \"%\" '{print $1}'").strip()
            # 查看丢包百分比
            # parse result
            assert result == '0'
            # net table count check
            m1 = ovs_flow.get_flow_packets_without_nw_src(n2_session, netX, 'dpdk0')
            assert m1 == 10
            m2 = ovs_flow.get_offload_flow_packets_without_nw_src(n2_session, netX, 'dpdk0')
            assert m2 == 9
            # 持续ping包
            host_session.execute_command('ping 7.7.7.7 &')
            # 热插拔
            n2_session.execute_command(f'qmp detach-device easy_bm {netX}.xml')
            n2_session.execute_command(f'qmp attach-device easy_bm {netX}.xml')
            # 重新up enX
            host_session.execute_command(f'ip link set dev {ensX} up && ip addr add 7.7.7.1/24 dev {ensX}')
            # host kill ping
            host_session.execute_command('kill -9 `pidof ping`')
            # prepare
            configure_net_table(n2_session, netX)
            # ping 10 个包
            result = host_session.execute_command(
                "ping 7.7.7.7 -c 10|grep loss|awk '{print $6}'|awk -F \"%\" '{print $1}'").strip()
            # 查看丢包百分比
            assert result == '0'
            # net table count check
            m1 = ovs_flow.get_flow_packets_without_nw_src(n2_session, netX, 'dpdk0')
            assert m1 == 10
            m2 = ovs_flow.get_offload_flow_packets_without_nw_src(n2_session, netX, 'dpdk0')
            assert m2 == 9
        finally:
            emu_net_teardown(it_session, ensX)
    elif it_session.env_type == EnvironmentType.HYBRID.name:
        pass
    else:
        raise TypeError(f"it_session.env_type error.it_session.env_type={it_session.env_type}")


def netpf_multidev_ovs_reconnect(it_session, dev_type, dev_queue_type):
    """
        功能：支持ovs进程断链后自动重连。

        参数：
        it_session: IT会话对象，集成测试会话。
        dev_type: 前端设备类型，‘net|blk|nvme’的其中一种。
        dev_queue_type:  后端队列类型，'Legacy|Modern|Packed'的其中一种。

        返回：
        函数没有明确返回值，但可能会通过it_session对设备进行
        示例：
        调用 netpf_multidev_ovs_reconnect(session, 'net', 'Legacy')
             测试Legacy网络设备支持ovs进程断链后自动重连。
    """
    # 0.pre 登录前后端成功,确认host端加载驱动成功
    n2_session, host_session = session_util.pretest(it_session, dev_type)
    src_ip = "185.233.190.2"
    if it_session.env_type == EnvironmentType.SIM.name:

        trexSendConf = get_trexSendConf_uplink_host(it_session, dev_type, dev_queue_type)

        ret = low_speed_path_test(it_session, trexSendConf)
        assert ret
        ret = offload_path_test(it_session, trexSendConf)
        assert ret

        # 在N2上ovs断链重连（SIM环境暂不支持该功能）
        pass
        logging.info(f'SIM环境暂不支持ovs断链重连的功能')

        ret = low_speed_path_test(it_session, trexSendConf)
        assert ret
        # 再发一个包验证offload
        ret = offload_path_test(it_session, trexSendConf)
        assert ret
    elif it_session.env_type == EnvironmentType.EMU.name or \
        it_session.env_type == EnvironmentType.CRB.name:
        pass
    elif it_session.env_type == EnvironmentType.HYBRID.name:
        pass
    else:
        raise TypeError(f"it_session.env_type error.it_session.env_type={it_session.env_type}")


def netpf_multidev_hyper_commander_reconnect(it_session, dev_type, dev_queue_type):
    """
        功能：支持hyper_commander进程断链后自动重连。

        参数：
        it_session: IT会话对象，集成测试会话。
        dev_type: 前端设备类型，‘net|blk|nvme’的其中一种。
        dev_queue_type:  后端队列类型，'Legacy|Modern|Packed'的其中一种。

        返回：
        函数没有明确返回值，但可能会通过it_session对设备进行
        示例：
        调用 netpf_multidev_hyper_commander_reconnect(session, 'net', 'Legacy')
             测试Legacy网络设备支持hyper_commander进程断链后自动重连。
    """
    # 0.pre 登录前后端成功,确认host端加载驱动成功
    n2_session, host_session = session_util.pretest(it_session, dev_type)
    src_ip = "185.233.190.2"
    if it_session.env_type == EnvironmentType.SIM.name:

        trexSendConf = get_trexSendConf_uplink_host(it_session, dev_type, dev_queue_type)

        ret = low_speed_path_test(it_session, trexSendConf)
        assert ret
        ret = offload_path_test(it_session, trexSendConf)
        assert ret

        # 在N2上hyper-commander断链重连（SIM环境暂不支持该功能）
        pass
        logging.info(f'SIM环境暂不支持hyper-commander断链重连的功能')

        ret = low_speed_path_test(it_session, trexSendConf)
        assert ret
        # 再发一个包验证offload
        ret = offload_path_test(it_session, trexSendConf)
        assert ret
    elif it_session.env_type == EnvironmentType.EMU.name or \
            it_session.env_type == EnvironmentType.CRB.name:
        # 准备工作
        interface = emu_net_prepare(it_session, dev_queue_type)
        netX = interface['up_tap']
        # ping 10 个包
        result = host_session.execute_command("ping 7.7.7.7 -c 10|grep loss|awk '{print $6}'|awk -F \"%\" '{print $1}'")
        # 查看丢包百分比
        # parse result
        assert result == '0'
        # net table count check
        m1 = ovs_flow.get_flow_packets_without_nw_src(n2_session, netX, 'dpdk0')
        assert m1 == 10
        m2 = ovs_flow.get_offload_flow_packets_without_nw_src(n2_session, netX, 'dpdk0')
        assert m2 == 9
        logging.info('---------------正在持续ping包')
        # 持续ping包
        host_session.execute_command("tmux new-window -n MyWindow 'ping 7.7.7.7'")
        # N2侧ovs断链重连
        n2_session.execute_command(
            'kill -9 `pidof ovs-vswitchd` && cd /usr/share/jmnd/single/debug_script/8net_8blk/ && ./2_underlay_ovs.sh')
        # host kill ping
        host_session.execute_command('tmux kill-window -t MyWindow')
        # 清空快慢表计数
        ovs_flow.del_flows(n2_session)
        n2_session.execute_command(
            f'ovs-ofctl add-flow br-ext in_port=dpdk0,action=output:{netX} && ovs-ofctl add-flow br-ext in_port={netX},action=output:dpdk0')
        # ping 10 个包
        result = host_session.execute_command("ping 7.7.7.7 -c 10|grep loss|awk '{print $6}'|awk -F \"%\" '{print $1}'")
        # 查看丢包百分比
        # parse result
        assert result == '0'
        # net table count check
        m1 = ovs_flow.get_flow_packets_without_nw_src(n2_session, 'net7', 'dpdk0')
        assert m1 == 10
        m2 = ovs_flow.get_offload_flow_packets_without_nw_src(n2_session, 'net7', 'dpdk0')
        assert m2 == 9
        # hyper-command 断链重连
        n2_session.execute_command('qmp destroy easy_bm && qmp create easy_bm.xml')
        # 等待host启动完成
        timeout = 1200
        # 2.获取host侧的ip地址
        ConfPage = it_session.get_configure()
        host_server = ConfPage.get_host_server()
        host_name = host_server.hostname

        # 3.拼接验证host端是否起的命令
        start_time = time.time()
        ping_host_cmd = f"Ping {host_name}"

        while True:
            out_put = subprocess_command(ping_host_cmd)

            current_time = time.time()
            elapsed_time = current_time - start_time

            if elapsed_time > timeout:
                logging.error("超时：host侧未重启成功")
                return False

            # 获取vhost进程数
            if {host_name} in out_put.decode('gbk'):
                logging.info("成功：host侧重启成功")
                break

            time.sleep(10)

        logging.info(f"\n-----------------------------冷重启输出结果:\n {out_put}")
        # disable RC timeout
        storage_util.disable_rc_timeout(host_session)
        # load virtio_net driver
        dev_util.load_driver(host_session, dev_type)
        # re-prepare
        ovs_flow.del_flows(n2_session)
        emu_net_prepare(it_session, dev_type, reprepare=True)
        # ping 10 个包
        result = host_session.execute_command("ping 7.7.7.7 -c 10|grep loss|awk '{print $6}'|awk -F \"%\" '{print $1}'")
        # 查看丢包百分比
        # parse result
        assert result == '0'
        # net table count check
        m1 = ovs_flow.get_flow_packets_without_nw_src(n2_session, 'net7', 'dpdk0')
        assert m1 == 10
        m2 = ovs_flow.get_offload_flow_packets_without_nw_src(n2_session, 'net7', 'dpdk0')
        assert m2 == 9

    elif it_session.env_type == EnvironmentType.HYBRID.name:
        pass
    else:
        raise TypeError(f"it_session.env_type error.it_session.env_type={it_session.env_type}")


def get_session(it_session, port_type):
    if port_type == "host":
        session = it_session.get_host_session()
    elif port_type == "N2":
        session = it_session.get_n2_session()
    else:
        raise Error("trexSendConf.output or input type{tyep} error")
    return session


def get_host_netdevs(host_session):
    """
    通过“ll /sys/class/net”去获取相应的网络设备
    """

    # 1. 执行”ll /sys/class/net“ 命令
    cmd = f'ls -l /sys/class/net'
    result = host_session.execute_command(cmd)
    logging.info(f"\n execute_command({cmd}):\n {result}")
    # 2. 解析 netdev
    virtio_interfaces = []
    net_lines = result.strip().split('\n')
    for line in net_lines:
        # 在 Virtio 网卡的设备名通常以 "v" 或 "virtio" 开头
        if 'virtio' in line:
            parts = line.split('/')
            if len(parts) >= 4:
                netdev = {}
                netdev['dev_name'] = parts[-1]
                pcie_num = parts[-4]
                netdev['pcie_num'] = pcie_num[-7:]
                mac_command = f"ip addr show {netdev['dev_name']}"
                output = host_session.execute_command(mac_command)
                result = output.strip()
                logging.info(f"--------------------------result:{result}")
                mac_match = re.search(r'link/ether ([\w:]+)', result)
                ipv4_match = re.search(r'inet ([\d.]+)/\d+', result)
                if mac_match:
                    netdev['mac_addr'] = mac_match.group(1)
                if ipv4_match:
                    netdev['ip_v4'] = ipv4_match.group(1)

                virtio_interfaces.append(netdev)
    logging.info(f"-------------------------------------virtio_interfaces:\n {virtio_interfaces}")
    """
    [{'dev_name': 'ens10', 'pcie_num': '0000:3e:02.0', 'mac_addr': '52:54:00:00:96:87'}, 
    {'dev_name': 'ens11', 'pcie_num': '0000:3e:02.0', 'mac_addr': '52:54:00:00:96:86'}, 
    {'dev_name': 'ens12', 'pcie_num': '0000:3e:02.0', 'mac_addr': '52:54:00:00:96:85'}, 
    {'dev_name': 'ens13', 'pcie_num': '0000:3e:02.0', 'mac_addr': '52:54:00:00:96:92'}, 
    {'dev_name': 'ens14', 'pcie_num': '0000:3e:02.0', 'mac_addr': '52:54:00:00:96:91'}, 
    {'dev_name': 'ens15', 'pcie_num': '0000:3e:02.0', 'mac_addr': '52:54:00:00:96:90'}, 
    {'dev_name': 'ens16', 'pcie_num': '0000:3e:02.0', 'mac_addr': '52:54:00:00:96:89'}, 
    {'dev_name': 'ens9', 'pcie_num': '0000:3e:02.0', 'mac_addr': '52:54:00:00:96:88'}]
    """

    if virtio_interfaces is None:
        logging.error(f"virtio_interfaces is None")
        raise GetNetworkInterfaceError("get virtio_interfaces error")

    return virtio_interfaces


def update_netdevs_of_source_path(it_session, host_virtio_interfaces):
    file_name = download_file_from_n2(it_session, Jmnd_file_name)
    domain_parser = EasyBmParser(file_name)
    file_interfaces = domain_parser.get_interfaces()
    for host_net in host_virtio_interfaces:
        for file_interface in file_interfaces:
            if host_net['mac_addr'] == file_interface['mac_address']:
                host_net['source_path'] = file_interface['source_path']
                break  # 只退出当前循环。
    return host_virtio_interfaces


def update_netdevs_of_source_path_with_dev_list(it_session, host_virtio_interfaces):
    n2_session = it_session.get_n2_session()
    dev_list = dev_util.get_dev_list(n2_session)
    host_interfaces = host_virtio_interfaces
    for dev in dev_list:
        for host_interface in host_interfaces:
            if host_interface['pcie_num'] == dev["bdf"]:
                source_path = change_devname_to_source_path(dev["dev_name"])
                host_interface["source_path"] = source_path

    return host_interfaces, dev_list


def update_netdevs_of_ovs_port(it_session, host_virtio_interfaces):
    """
    函数的功能相当于给ensX设备获取到N2侧的对应设备的 ['ovs_uptap': 'net2', 'ovs_queues': '8']
    """
    n2_session = it_session.get_n2_session()
    cmd = 'ovs-vsctl show'

    # 如果执行'ovs-vsctl show命令获取不到结果，可能需要配置环境变量
    # cmd_paths = "export PATH=$PATH:/usr/share/jmnd/bin/ovs/images/bin"
    # n2_session.execute_command(cmd_paths)
    # cmd_path = "printenv"
    # result = n2_session.execute_command(cmd_path)
    # logging.info(f"\n---------------------------环境变量是:{result}")

    timeout = 30
    start_time = time.time()
    ovs_show_output = ""

    while True:
        current_time = time.time()
        elapsed_time = current_time - start_time

        if elapsed_time > timeout:
            logging.error("超时：获取不到ovs_show")
            break
        # 获取vhost进程数
        ovs_show_output = n2_session.execute_command(cmd)

        if ovs_show_output:
            logging.info(
                f"\n---------------------------n2_sessilon.execute_command(ovs-vsctl show)\n:{ovs_show_output}")
            break

        # 间隔10秒再次获取实时结果
        time.sleep(2)

    assert ovs_show_output != "", "获取不到ovs_show!"
    """
    Port net0
        Interface net0
            type: dpdk
            options: {dpdk-devargs="net_jmnd0,iface=/tmp/sock0,client=1,queues=8", n_rxq="8", n_rxq_desc="256", n_txq_desc="256"}
        """
    parser = OVSPortParser(ovs_show_output)
    parser.parse()

    # 打印ovs_vsctl show信息
    ovs_ports = parser.print_ports()

    for ovs_port in ovs_ports:
        logging.info(f"-------------{ovs_port}\n")

    for host_net in host_virtio_interfaces:
        for ovs_port in parser.ports:
            if ovs_port.port_type == 'dpdk' and 'iface' in ovs_port.options and host_net['source_path'] == \
                    ovs_port.options['iface']:
                host_net['ovs_uptap'] = ovs_port.interface_name
                host_net['ovs_queues'] = ovs_port.options['queues']
                break
    return host_virtio_interfaces


def get_host_interfaces(it_session):
    """
    host_interfaces:
    [{'dev_name': 'ens10', 'pcie_num': '0000:3e:02.0', 'mac_addr': '52:54:00:00:96:86'},
    {'dev_name': 'ens11', 'pcie_num': '0000:3e:02.0', 'mac_addr': '52:54:00:00:96:85'},
    {'dev_name': 'ens12', 'pcie_num': '0000:3e:02.0', 'mac_addr': '52:54:00:00:96:92'},
    {'dev_name': 'ens13', 'pcie_num': '0000:3e:02.0', 'mac_addr': '52:54:00:00:96:91'},
    {'dev_name': 'ens14', 'pcie_num': '0000:3e:02.0', 'mac_addr': '52:54:00:00:96:90'},
    {'dev_name': 'ens15', 'pcie_num': '0000:3e:02.0', 'mac_addr': '52:54:00:00:96:89'},
    {'dev_name': 'ens16', 'pcie_num': '0000:3e:02.0', 'mac_addr': '52:54:00:00:96:88'},
    {'dev_name': 'ens9', 'pcie_num': '0000:3e:02.0', 'mac_addr': '52:54:00:00:96:87'}]
    """

    # 1.获取会话
    host_session = it_session.get_host_session()

    # 2.获取host端所有ensX网口和mac_add ip_v4 {'dev_name': 'ens10', 'pcie_num': '4a:00.0', 'mac_addr': '52:54:00:00:96:87'}
    host_interfaces = get_host_netdevs(host_session)

    # 3.获取N2端与host端ensX映射，并更新host端的source_path与N2
    host_interfaces, dev_list = update_netdevs_of_source_path_with_dev_list(it_session, host_interfaces)
    # {'dev_name': 'ens10', 'pcie_num': '4a:00.0', 'mac_addr': '52:54:00:00:96:87','source_path': '/tmp/sock2'}

    logging.info(f"---------------------------host_interfaces_source_path:\n{host_interfaces}")

    logging.info(f"---------------------------dev_list:\n{dev_list}")

    host_interfaces = update_netdevs_of_ovs_port(it_session, host_interfaces)
    logging.info(f"---------------------------host_interfaces_ovs_port:\n{host_interfaces}")

    """
    [{'dev_name': 'ens10', 'pcie_num': '4a:00.0', 'mac_addr': '52:54:00:00:96:87', 'source_path': '/tmp/sock2', 'ovs_uptap': 'net2', 'ovs_queues': '8'}, 
    {'dev_name': 'ens11', 'pcie_num': '4b:00.0', 'mac_addr': '52:54:00:00:96:86', 'source_path': '/tmp/sock1', 'ovs_uptap': 'net1', 'ovs_queues': '8'}, 
    {'dev_name': 'ens12', 'pcie_num': '4c:00.0', 'mac_addr': '52:54:00:00:96:85', 'source_path': '/tmp/sock0', 'ovs_uptap': 'net0', 'ovs_queues': '8'}, 
    {'dev_name': 'ens13', 'pcie_num': '4d:00.0', 'mac_addr': '52:54:00:00:96:92', 'source_path': '/tmp/sock7', 'ovs_uptap': 'net7', 'ovs_queues': '8'}, 
    {'dev_name': 'ens14', 'pcie_num': '4e:00.0', 'mac_addr': '52:54:00:00:96:91', 'source_path': '/tmp/sock6', 'ovs_uptap': 'net6', 'ovs_queues': '8'}, 
    {'dev_name': 'ens15', 'pcie_num': '4f:00.0', 'mac_addr': '52:54:00:00:96:90', 'source_path': '/tmp/sock5', 'ovs_uptap': 'net5', 'ovs_queues': '8'}, 
    {'dev_name': 'ens16', 'pcie_num': '50:00.0', 'mac_addr': '52:54:00:00:96:89', 'source_path': '/tmp/sock4', 'ovs_uptap': 'net4', 'ovs_queues': '8'}, 
    {'dev_name': 'ens9', 'pcie_num': '49:00.0', 'mac_addr': '52:54:00:00:96:88', 'source_path': '/tmp/sock3', 'ovs_uptap': 'net3', 'ovs_queues': '8'}]
    """

    return host_interfaces, dev_list


def get_random_two_netdevs(virtio_interfaces):
    # 随机选择两个网卡
    if virtio_interfaces:
        if len(virtio_interfaces) >= 2:
            random_interfaces = random.sample(virtio_interfaces, 2)
        else:
            random_interfaces = virtio_interfaces
        return random_interfaces
    else:
        logging.error("virtio_interfaces is None")
        raise Error("virtio_interfaces is None")


def change_devname_to_source_path(devname):
    """
    devname: n2 的devname
    """
    # 使用`str.split`方法切分字符串
    split_str = devname.split("_", 1)[1]  # 通过`_`切分字符串，并取第二部分

    # 分别获取 'tmp' 和 'sock1'
    tmp, sock = split_str.split("_", 1)  # 通过`_`再次切分字符串，并分别赋值给变量

    # 使用`str.join`方法重新连接字符串
    source_path = "/" + "/".join([tmp, sock])  # 通过`/`连接字符串，并在前面添加`/`
    return source_path


def get_matched_netdev(n2_session, host_virtio_interfaces, dev_queue_type, dev_list=None):
    # 1. 进入后端诊断模块msg_cmd，输入查询命令device list,并把结果解析。
    if dev_list is None:
        dev_list = dev_util.get_dev_list(n2_session)
    if dev_queue_type == 'Legacy':
        matched_devices = dev_util.get_legacy_dev_by_dev_name(dev_list, "net")
    elif dev_queue_type == 'Modern':
        matched_devices = dev_util.get_modern_dev_by_dev_name(dev_list, "net")
    elif dev_queue_type == 'Packed':
        matched_devices = dev_util.get_packed_dev_by_dev_name(dev_list, "net")
    else:
        raise Error(f"dev_queue_type({dev_queue_type}) error!")

    matched_virtio_net = []
    virtio_nets = host_virtio_interfaces
    logging.info(f'dev_queue_type:{dev_queue_type},\n matched_devices is:\n{matched_devices}\n'
                 f'virtio_net is:\n{virtio_nets}')
    for dev in virtio_nets:
        for matched_dev in matched_devices:
            source_path = change_devname_to_source_path(matched_dev['dev_name'])
            if dev['source_path'] == source_path:
                matched_virtio_net.append(dev)
    logging.info(f'----------------------------------matched_virtio_net=\n {matched_virtio_net}')
    return matched_virtio_net


def remove_matched_interfaces(host_interfaces, test_interfaces):
    for netdev in host_interfaces:
        for interface in test_interfaces:
            if netdev['source_path'] == interface['source_path']:
                host_interfaces.remove(netdev)
    return host_interfaces


def choice_two_ens(host_interfaces, matched_host_interfaces):
    # 随机选择两个网卡
    if len(host_interfaces) == 0:
        raise Error("host_interfaces is None")
    if len(matched_host_interfaces) == 0:
        raise Error("matched_host_interfaces is None")
    # 当matched_netdev 设备 >= 2 时，随机选出2个设备进行测试
    if len(matched_host_interfaces) >= 2:
        interface1, interface2 = random.sample(matched_host_interfaces, 2)
    elif len(matched_host_interfaces) == 1:
        interface1 = matched_host_interfaces[0]
        other_host_virtio_interfaces = remove_matched_interfaces(host_interfaces, matched_host_interfaces)
        interface2 = random.sample(other_host_virtio_interfaces, 1)

    return interface1, interface2


def get_test_host_ens(it_session, dev_type, dev_queue_type):
    if it_session.env_type == EnvironmentType.SIM.name:

        # 获取host上所有的ens
        host_interfaces, dev_list = get_host_interfaces(it_session)
        logging.info(f"host_interfaces:\n{host_interfaces}")
        """
           [{'dev_name': 'ens10', 'pcie_num': '4a:00.0', 'mac_addr': '52:54:00:00:96:87', 'source_path': '/tmp/sock2', 'ovs_uptap': 'net2', 'ovs_queues': '8'}]
        """
        matched_host_interfaces = get_matched_netdev_by_dev_list(host_interfaces, dev_list, dev_queue_type)
        # 当matched 的设备>=2时，随机选出2个设备进行测试
        interface1, interface2 = choice_two_ens(host_interfaces, matched_host_interfaces)
    elif it_session.env_type == EnvironmentType.EMU.name or \
            it_session.env_type == EnvironmentType.CRB.name:
        # 获取host上所有的ens
        host_interfaces, dev_list = get_host_interfaces(it_session)
        logging.info(f"host_interfaces:\n{host_interfaces}")
        """
           [{'dev_name': 'ens10', 'pcie_num': '4a:00.0', 'mac_addr': '52:54:00:00:96:87', 'source_path': '/tmp/sock2', 'ovs_uptap': 'net2', 'ovs_queues': '8'}]
        """
        matched_host_interfaces = get_matched_netdev_by_dev_list(host_interfaces, dev_list, dev_queue_type)
        # 当matched 的设备>=2时，随机选出2个设备进行测试
        interface1, interface2 = choice_two_ens(host_interfaces, matched_host_interfaces)
    elif it_session.env_type == EnvironmentType.HYBRID.name:
        pass
    else:
        raise TypeError(f"it_session.env_type error.it_session.env_type={it_session.env_type}")
    logging.info(f'----------------------------------interface1：{interface1} interface2：{interface2}\n')

    return interface1, interface2


def get_matched_netdev_by_dev_list(host_virtio_interfaces, dev_list, dev_queue_type):
    # 1. 进入后端诊断模块msg_cmd，输入查询命令device list,并把结果解析。
    # dev_list = dev_util.get_dev_list(n2_session)
    if dev_queue_type == 'Legacy':
        matched_devices = dev_util.get_legacy_dev_by_dev_name(dev_list, "net")
    elif dev_queue_type == 'Modern':
        matched_devices = dev_util.get_modern_dev_by_dev_name(dev_list, "net")
    elif dev_queue_type == 'Packed':
        matched_devices = dev_util.get_packed_dev_by_dev_name(dev_list, "net")
    else:
        raise Error(f"dev_queue_type({dev_queue_type}) error!")

    matched_virtio_net = []
    virtio_nets = host_virtio_interfaces
    logging.info(f'dev_queue_type:{dev_queue_type},\n matched_devices is:\n{matched_devices}\n'
                 f'virtio_blocks is:\n{virtio_nets}')
    for dev in virtio_nets:
        for matched_dev in matched_devices:
            source_path = change_devname_to_source_path(matched_dev['dev_name'])
            if dev['source_path'] == source_path:
                matched_virtio_net.append(dev)
    logging.info(f'----------------------------------matched_virtio_net=\n {matched_virtio_net}')
    return matched_virtio_net


def config_ovs_flow(n2_session, trexSendConf):
    trex_inport = trexSendConf.inport
    trex_outport = trexSendConf.outport
    ovs_flow.del_flows(n2_session)
    ovs_flow.add_flows(n2_session, trex_inport.ovs_tap, trex_inport.src_ip, trex_outport.ovs_tap)
    return True


def config_trex(it_session, trexSendConf, timeout=30):
    """
    功能：配置trex
        trex_cfg.yaml 端口配置有：
        1. inport在host端，且inport和output都在host端
        2. inport在host端，但output在N2端
        3. inport在N2端，且inport和output都在N2端
        4. inport在N2端，但output在host端
    """
    inport_session = get_session(it_session, trexSendConf.inport.port_type)
    inport_session_type = trexSendConf.inport.port_type
    output_session_type = trexSendConf.outport.port_type
    if inport_session_type == "host" and output_session_type == "host":
        trex_cfg_interfaces1 = trexSendConf.inport.port_name
        trex_cfg_interfaces2 = trexSendConf.outport.port_name
        inport_server_conf = it_session.get_configure().get_host_server()
    elif inport_session_type == "host" and output_session_type == "N2":
        trex_cfg_interfaces1 = trexSendConf.inport.port_name
        trex_cfg_interfaces2 = "virbr0"
        inport_server_conf = it_session.get_configure().get_host_server()
    elif inport_session_type == "N2" and output_session_type == "host":
        trex_cfg_interfaces1 = trexSendConf.inport.port_name
        trex_cfg_interfaces2 = "macif1"
        inport_server_conf = it_session.get_configure().get_n2_server()
    elif inport_session_type == "N2" and output_session_type == "N2":
        pass
    trex_util.scp_trex_cfg_yaml_to_trex_server(inport_server_conf)
    trex_util.config_trex_cfg_yaml_on_trex_server(inport_session, trex_cfg_interfaces1,
                                                  trex_cfg_interfaces2)
    logging.info("config_trex successed")
    return True


def prepare_for_sent_trex_package(it_session, trexSendConf, timeout=30):
    """
    功能：trex 发流前准备
          1)启动trex-server
          2)启动trex-console 准备发流
          3)启动tcpdump 准备抓包
    """
    inport_session = get_session(it_session, trexSendConf.inport.port_type)
    output_session = get_session(it_session, trexSendConf.outport.port_type)

    # 3.1启动trex-server
    ret = trex_util.start_trex_server(inport_session, timeout)
    assert ret
    logging.info(f"3.1启动trex-server 成功")

    # 3.2启动trex-console
    ret = trex_util.start_trex_console(inport_session, timeout)
    assert ret
    logging.info(f"3.2启动trex-console 成功")

    # 发包前先启动tcpdump抓包命令
    # 3.3 启动tcpdump 准备抓包
    ret = start_tcpdump(output_session, trexSendConf.outport.port_name, trexSendConf.inport.src_ip)
    assert ret
    logging.info(f"3.3在N2 上启动tcpdump 准备抓包 成功")
    return True


# def sent_trex_package_from_N2(it_session,trexSendConf):
#     # 拷贝trex_cfg.yaml文件到trex运行环境，并修改配置
#     host_session = it_session.get_N2_session()
#     trex_util.scp_trex_cfg_yaml_to_trex_server(it_session, trexSendConf.inport.type)
#     trex_util.config_trex_cfg_yaml_on_trex_server(host_session, trexSendConf.inport.port_name, trexSendConf.outport.port_name)
#     # 在trex运行环境上先后启动trex-server及trex-console
#     trex_util.start_trex_server(host_session)
#     trex_util.start_trex_console(host_session)

def ovs_offload_check(n2_session, trexSendConf, package_num, timeout=30):
    """
    功能：N2上ovs-appctl dpctl/dump-flows -m查看快表已生成
    """
    # 查看流表计数
    ovs_inport = trexSendConf.inport.ovs_tap
    ovs_output = trexSendConf.outport.ovs_tap
    src = trexSendConf.inport.src_ip

    start_time = time.time()
    offload_package_num = package_num - 1

    while True:
        # 获取当前的包数
        num = ovs_flow.get_offload_flow_packets(n2_session, ovs_inport, src, ovs_output)
        logging.info(f"\n-------------------------------num:{num}")

        if isinstance(num, int):
            num_result = num
        else:
            num_result = int(num[0])

        # 检查是否满足条件
        if num_result == offload_package_num:
            result = True
            break

        # 检查是否超时（30秒）
        if time.time() - start_time > timeout:
            result = False
            raise Exception(f'错误：卸载流表计数不为{offload_package_num}！且超时30秒。')

        # 等待2秒再次检查
        time.sleep(2)
    return result


def ovs_ofctl_check(n2_session, trexSendConf, expect_num):
    """
    功能：N2上ovs-ofctl dump-flows br-ext查看流表计数为expect_num
    """
    # 查看流表计数
    ovs_inport = trexSendConf.inport.ovs_tap
    ovs_output = trexSendConf.outport.ovs_tap
    src = trexSendConf.inport.src_ip

    for i in range(10):
        num = ovs_flow.get_flow_packets(n2_session, ovs_inport, src, ovs_output)
        if int(num[0]) == expect_num:
            break
        elif int(num[0]) != expect_num and i == 9:
            raise Exception(f'错误：流表计数不为{expect_num}！')
            return False
    return True


def trex_send_packet(it_session, trexSendConf):
    """
       功能：在trex-console 里发第一个包
    """
    inport_session_type = trexSendConf.inport.port_type
    if inport_session_type == "host":
        inport_session = it_session.get_host_session()
    elif inport_session_type == "N2":
        inport_session = it_session.get_n2_session()
    else:
        raise Error(f"trexSendConf.inport type{inport_session_type} error")
    result = send_packet_on_trex_console(inport_session, 0)
    return result


def check_the_first_packet(it_session, trexSendConf):
    """
       功能：检查收到的第一个包的正确性
           1）output 所在端 tcpdump可以抓到1个包
           2）N2上ovs-ofctl dump-flows br-ext查看流表计数为1
           3）N2上ovs-appctl dpctl/dump-flows -m查看快表已生成，且计数为0，代表首包已上送
    """
    output_session = get_session(it_session, trexSendConf.outport.port_type)
    n2_session = it_session.get_n2_session()

    # 1）output 所在端 tcpdump可以抓到1个包
    result = check_tcpdump_result(output_session, trexSendConf.inport.src_ip)
    if result is not True:
        logging.info(f"5.1 output 所在端 tcpdump 无法抓到包")
        return False
    logging.info(f"5.1 output 所在端 tcpdump可以抓到1个包")
    # 2）N2上ovs-ofctl dump-flows br-ext查看流表计数为1
    package_num = 1
    result = ovs_ofctl_check(n2_session, trexSendConf, package_num)
    if result is not True:
        logging.info(f"5.2 N2上ovs-ofctl dump-flows br-ext查看流表计数不为{package_num}")
        return False
    logging.info(f"5.2 N2上ovs-ofctl dump-flows br-ext查看流表计数为为{package_num}")

    # 3）N2上ovs-appctl dpctl/dump-flows -m查看快表已生成，且计数为0，代表首包已上送
    result = ovs_offload_check(n2_session, trexSendConf, package_num)
    if result is not True:
        logging.info(f"5.3 N2上ovs-appctl dpctl/dump-flows -m计数错误。")
        return False
    logging.info(f"5.3 N2上ovs-appctl dpctl/dump-flows -m查看快表已生成，且计数为0，代表首包已上送")
    return True


def check_packet(it_session, trexSendConf, package_num=1):
    """
       功能：检查收到的第二包的正确性
           1）output 所在端 tcpdump可以抓到1个包
           2）N2上ovs-ofctl dump-flows br-ext查看流表计数为1
           3）N2上ovs-appctl dpctl/dump-flows -m查看快表已生成，且计数为0，代表首包已上送
    """
    output_session = get_session(it_session, trexSendConf.outport.port_type)
    n2_session = it_session.get_n2_session()

    # 1）output 所在端 tcpdump可以抓到1个包
    result = check_tcpdump_result(output_session, trexSendConf.inport.src_ip, package_num)
    if result is not True:
        logging.info(f"5.1 output 所在端 tcpdump 无法抓到包")
        return False
    logging.info(f"5.1 output 所在端 tcpdump可以抓到1个包")
    # 2）N2上ovs-ofctl dump-flows br-ext查看流表计数为package_num
    result = ovs_ofctl_check(n2_session, trexSendConf, package_num)
    if result is not True:
        logging.info(f"5.2 N2上ovs-ofctl dump-flows br-ext查看流表计数不为{package_num}")
        return False
    logging.info(f"5.2 N2上ovs-ofctl dump-flows br-ext查看流表计数为为{package_num}")

    # 3）N2上ovs-appctl dpctl/dump-flows -m查看快表已生成，且计数为package_num-1，代表首包已上送
    result = ovs_offload_check(n2_session, trexSendConf, package_num)
    if result is not True:
        logging.info(f"5.3 N2上ovs-appctl dpctl/dump-flows -m计数错误。")
        return False
    logging.info(f"5.3 N2上ovs-appctl dpctl/dump-flows -m查看快表已生成")
    return True


def trex_send_one_packet_and_check_from_host(it_session, trexSendConf):
    inport_session_type = trexSendConf.inport.port_type
    if inport_session_type == "host":
        inport_session = it_session.get_host_session()
    elif inport_session_type == "N2":
        inport_session = it_session.get_n2_session()
    else:
        raise Error(f"trexSendConf.inport type{inport_session_type} error")
    outport_session_type = trexSendConf.outport.port_type
    if outport_session_type == "host":
        outport_session = it_session.get_host_session()
    elif outport_session_type == "N2":
        outport_session = it_session.get_n2_session()
    else:
        raise Error(f"trexSendConf.outport type={outport_session_type} error")

    # 发包前先启动tcpdump抓包命令
    start_tcpdump_one_packet(inport_session, trexSendConf.outport.port_name, trexSendConf.inport.src_ip)
    # trex从0口发一个包
    send_one_packet_on_trex_console(inport_session, 0)
    # 查看tcpdump抓包结果

    result = check_tcpdump_result(outport_session, trexSendConf.inport.src_ip)
    assert result

    n2_session = it_session.get_n2_session()
    expect_num = 1
    ovs_ofctl_check(n2_session, trexSendConf, expect_num)


def sim_random_get_macport(num):
    sim_macport = []
    for i in range(2):
        item = {'dev_name': f'macif{i}', 'ovs_tap': f'vnet{i}'}
        sim_macport.append(item)

    return random.sample(sim_macport, num)


# net-testcase: modify active qp num repeatedly
def emu_net_prepare(it_session, dev_queue_type, reprepare=False, host_reprepare_only=False):
    # host prepare
    # view the ens device
    host_session = it_session.get_host_session()
    n2_session = it_session.get_n2_session()
    host_interfaces, dev_list = get_host_interfaces(it_session)

    # parse the result string, get the ensX
    matched_host_interfaces = get_matched_netdev(n2_session, host_interfaces, dev_queue_type, dev_list)

    # 在host interfaces中随便选一个
    # interface = random.choice(matched_host_interfaces)
    # 现在先写死ens9
    interface = None
    for host_interface in host_interfaces:
        if host_interface['dev_name'] == 'ens9':
            interface = host_interface
            break

    ensX = interface['dev_name']

    # configure ip address
    host_session.execute_command(f'ip link set dev {ensX} up && ip addr add 7.7.7.1/24 dev {ensX}')

    if host_reprepare_only:
        return interface

    # n2 prepare

    if not reprepare:  # 如果重新准备，那这一步可以跳过，因为之前已经配置过
        n2_session.execute_command(
            'ovs-vsctl add-port br-ext dpdk0 -- set Interface dpdk0 type=dpdk options:dpdk-devargs=0000:01:00.1 options:n_txq=8 options:n_rxq=8 options:n_rxq_desc=2048 options:n_txq_desc=2048 ofport_request=1')

    # 获取匹配的net设备
    netX = interface['ovs_uptap']
    logging.info(f'------------------------配置的net设备是：{netX}.')
    # add net table
    cmd1 = f'ovs-ofctl add-flow br-ext in_port=dpdk0,action=output:{netX}'
    n2_session.execute_command(cmd1)
    cmd2 = f'ovs-ofctl add-flow br-ext in_port={netX},action=output:dpdk0'
    n2_session.execute_command(cmd2)
    cmd = cmd1 + '\n' + cmd2
    # 打印检查
    logging.info(f'-----------------------------配置流表的命令是：{cmd}')
    # 检查一下
    result = n2_session.execute_command(f'ovs-ofctl dump-flows br-ext --names')
    logging.info(f'---------------------------查询慢表结果：{result}')
    assert result

    # test device configuration
    # to-do

    # sends data to the tester through the macport0 port
    host_session = it_session.get_host_session()
    cnt = 0
    is_success = False
    while cnt < 10 and not is_success:  # 如果10次都失败，那么就无法ping 通
        logging.info(f'--------------------------第{cnt + 1}次尝试连接测试仪-------------------------')
        is_success = ping_test_0_loss_rate(host_session, '7.7.7.7')
        # 重新配流表
        configure_net_table(it_session.get_n2_session(), netX)
        cnt += 1

    assert is_success, '无法联通测试仪接口'
    return interface
    # end


def get_host_qp_and_n2_qp_value(it_session, interface1, interface2):
    # get maximum qp num and current qp num (host)
    host_session = it_session.get_host_session()
    qp_values = get_net_qp(host_session, interface1)
    # get n2 qp num
    n2_session = it_session.get_n2_session()
    n2_qp_value = None
    cmd = 'ovs-vsctl show'
    ovs_show_output = n2_session.execute_command(cmd)
    logging.info(f"\n---------------------------ovs_show_output:{ovs_show_output}")
    """
    Port net0
        Interface net0
            type: dpdk
            options: {dpdk-devargs="net_jmnd0,iface=/tmp/sock0,client=1,queues=8", n_rxq="8", n_rxq_desc="256", n_txq_desc="256"}
        """
    parser = OVSPortParser(ovs_show_output)
    parser.parse()
    # 打印ovs_vsctl show信息
    logging.info(f"\n---------------------------parser:{parser.ports}")

    for ovs_port in parser.ports:
        if ovs_port.port_type == 'dpdk' and 'iface' in ovs_port.options and ovs_port.port_name == interface2:
            n2_qp_value = ovs_port.options['queues']
            break
    qp_values.append(n2_qp_value)
    # check
    logging.info(
        f'-------------------------------qp_values_len is {len(qp_values)}, qp[0] is {qp_values[0]}, qp[1] is {qp_values[1]}, qp[2] is {qp_values[2]}')
    return qp_values


def ping_test_0_loss_rate(host_session, target_ip):
    cmd = f"ping {target_ip} -c 1 " + "|grep loss|awk '{print $6}'|awk -F \"%\" '{print $1}'"
    ping_output = host_session.execute_command(cmd)
    logging.info(f'-----------------execute command is {cmd}--ping_output is ' + ping_output)
    if ping_output.strip() == '0':
        return True
    else:
        return False


def emu_net_teardown(it_session, ensX):
    # 将之前分配给interface 的ip地址回收
    host_session = it_session.get_host_session()
    host_session.execute_command(f'ip addr del 7.7.7.1/24 dev {ensX}')
    # 清fast table and slow table
    n2_session = it_session.get_n2_session()
    n2_session.execute_command('ovs-ofctl del-flows br-ext')
    while True:
        result = n2_session.execute_command('ovs-appctl revalidator/purge')
        if result:
            continue
        else:
            break
    # 将ensX口重新配置成8
    host_session.execute_command(f'ethtool -L {ensX} combined 8')
    # 检查是否配置成功
    combined_values = get_net_qp(host_session, ensX)
    logging.info(f"最后将{ensX}的值重新配成:{combined_values[1]}")
    assert int(combined_values[1]) == 8, f'最后清理资源出错，无法将{ensX}的当前qp值配置成8！'


def configure_net_table(n2_session, netX):
    logging.info('-----------正在重新配置流表：')
    # 清流表
    # 清fast table and slow table
    n2_session.execute_command('ovs-ofctl del-flows br-ext')
    while True:
        result = n2_session.execute_command('ovs-appctl revalidator/purge')
        if result:
            continue
        else:
            break

    # add net table
    cmd1 = f'ovs-ofctl add-flow br-ext in_port=dpdk0,action=output:{netX}'
    n2_session.execute_command(cmd1)
    cmd2 = f'ovs-ofctl add-flow br-ext in_port={netX},action=output:dpdk0'
    n2_session.execute_command(cmd2)
    cmd = cmd1 + '\n' + cmd2
    # 打印检查
    logging.info(f'-----------------------------再次！！ 配置流表的命令是：{cmd}')
    # 检查一下
    result = n2_session.execute_command(f'ovs-ofctl dump-flows br-ext --names')
    logging.info(f'---------------------------再次！！ 查询慢表结果：{result}')
    assert result
