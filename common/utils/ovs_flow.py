# -*- coding: utf-8 -*-

import logging
import re


def add_quotes_if_underscore_present(input_string):
    if '_' in input_string:
        return f'"{input_string}"'
    else:
        return input_string


def get_flow_packets(session, in_port, nw_src, output):
    """
    使用如下命令查看流表计数
    ovs-ofctl dump-flows br-ext
    结果示例：
     cookie=0x0, duration=257.223s, table=0, n_packets=1, n_bytes=34, ip,in_port="net_jmnd1",nw_src=185.233.190.2
     actions=output:"net_jmnd2"
    """
    cmd = f'ovs-ofctl dump-flows br-ext --names'
    result = session.execute_command(cmd)
    logging.info(f"\n execute_command({cmd}):\n {result}")
    flow_lines = result.strip().split('\n')
    in_port = add_quotes_if_underscore_present(in_port)
    output = add_quotes_if_underscore_present(output)
    flag = f'in_port={in_port},nw_src={nw_src} actions=output:{output}'
    packets_num = 0
    for line in flow_lines:
        if flag in line:
            packets_num = re.findall(r'n_packets=(\d+)', line)  # 提取抓包的数量
            break
        else:
            raise Exception('错误：没有找到对应的流表')

    return packets_num


def get_offload_flow_packets(n2_session, in_port, nw_src, output):
    """
    使用如下命令查看流表计数
    ovs-appctl dpctl/dump-flows -m |grep offloaded:yes |grep -v drop
    结果示例：
    ufid:7d9272f9-e67f-4a5c-9c65-f459b099ba1a, skb_priority(0/0),skb_mark(0/0),ct_state(0/0),ct_zone(0/0),
    ct_mark(0/0),ct_label(0/0),recirc_id(0),dp_hash(0/0),in_port(net_jmnd1),packet_type(ns=0,id=0),
    eth(src=00:01:00:00:00:02/00:00:00:00:00:00,dst=04:02:03:04:05:06/00:00:00:00:00:00),eth_type(0x0800),
    ipv4(src=185.233.190.2,dst=172.0.1.1/0.0.0.0,proto=0/0,tos=0/0,ttl=64/0,frag=no), packets:15,
     bytes:510, dpe_packets:15, dpe_bytes:510,used:169.207s, offloaded:yes, dp:dpdk,
     actions:net_jmnd2, dp-extra-info:miniflow_bits(4,2)

 ufid:2fc206e0-1efc-4e6d-ac65-e430bff08ad4, skb_priority(0/0),skb_mark(0/0),ct_state(0/0),ct_zone(0/0),ct_mark(0/0),ct_label(0/0),recirc_id(0),dp_hash(0/0),in_port(net4),packet_type(ns=0,id=0),eth(src=00:01:00:00:00:02/00:00:00:00:0
0:00,dst=04:02:03:04:05:06/00:00:00:00:00:00),eth_type(0x0800),ipv4(src=185.233.190.2,dst=172.0.1.1/0.0.0.0,proto=0/0,tos=0/0,ttl=64/0,frag=no), packets:0, bytes:0, dpe_packets:0, dpe_bytes:0,used:never, offloaded:yes, dp:dpdk, acti
ons:net5, dp-extra-info:miniflow_bits(4,2)

    """
    cmd = f'ovs-appctl dpctl/dump-flows -m |grep offloaded:yes |grep -v drop'
    result = n2_session.execute_command(cmd)
    # flow_lines = result.strip().replace('\n', '')
    flow_lines = result.strip().split('\n')

    logging.info(f"-----------------------------execute_command({cmd}):\n {result}")

    flag1 = f'in_port({in_port})'
    flag2 = f'src={nw_src}'
    flag3 = f'actions:{output}'

    logging.info(f"-----------------------------flag1={flag1} flag2={flag2} flag3={flag3}\n")
    dpe_packets_num = 0
    for line in flow_lines:
        if (flag1 in line) and (flag2 in line) and (flag3 in line):
            # dpe_packets_num = re.findall(r'dpe_packets:(\d+)', line)
            dpe_packets_num = re.findall(r'packets:(\d+)', line)
            break
        # else:
        #     raise Exception('错误：没有找到对应的流表')
    return dpe_packets_num


def del_flows(session):
    """
    清除流表
    ovs-ofctl del-flows br-ext   # 清慢表
    ovs-appctl revalidator/purge   # 清快表
    """
    cmd = f'ovs-ofctl del-flows br-ext;ovs-appctl revalidator/purge'
    result = session.execute_command(cmd)
    logging.info(f"\n execute_command({cmd}):\n {result}")

    cmd = f'ovs-ofctl dump-flows br-ext;ovs-appctl dpctl/dump-flows -m |grep offloaded:yes |grep -v drop'
    result = session.execute_command(cmd)
    result = result.strip().split('\n')
    if "NXST_FLOW reply (xid=0x4):" in result:
        result = result.remove("NXST_FLOW reply (xid=0x4):")
    if result:
        raise Exception('错误：流表有残留')


def add_flows(session, in_port, nw_src, output):
    """
    添加流表
    示例：从vnet0发出的，且符合源IP地址是185.233.190.2的所有流量都会被转发给net_jmnd1口
    ovs-ofctl add-flow br-ext nw_src=185.233.190.2,dl_type=0x0800,in_port=vnet0,action=output:net_jmnd1
    """
    cmd = f'ovs-ofctl add-flow br-ext nw_src={nw_src},dl_type=0x0800,in_port={in_port},action=output:{output}'
    session.execute_command(cmd)

    # 获取流表计数
    packets_num = get_flow_packets(session, in_port, nw_src, output)
    if int(packets_num[0]) != 0:
        raise Exception('错误：流表初始计数不为0！')

def get_flow_packets_without_nw_src(session, in_port, output):
    """
    使用如下命令查看流表计数
    ovs-ofctl dump-flows br-ext
    结果示例：
     cookie=0x0, duration=257.223s, table=0, n_packets=1, n_bytes=34, ip,in_port="net_jmnd1",nw_src=185.233.190.2
     actions=output:"net_jmnd2"
    """
    cmd = f'ovs-ofctl dump-flows br-ext --names'
    result = session.execute_command(cmd)
    logging.info(f"\n execute_command({cmd}):\n {result}")
    flow_lines = result.strip().split('\n')
    in_port = add_quotes_if_underscore_present(in_port)
    output = add_quotes_if_underscore_present(output)
    flag = f'in_port={in_port} actions=output:{output}'
    packets_num = 0
    for line in flow_lines:
        if flag in line:
            packets_num = re.findall(r'n_packets=(\d+)', line)  # 提取抓包的数量
            break
        else:
            raise Exception('错误：没有找到对应的流表')

    return packets_num


def get_offload_flow_packets_without_nw_src(n2_session, in_port, output):
    """
    使用如下命令查看流表计数
    ovs-appctl dpctl/dump-flows -m |grep offloaded:yes |grep -v drop
    结果示例：
    ufid:7d9272f9-e67f-4a5c-9c65-f459b099ba1a, skb_priority(0/0),skb_mark(0/0),ct_state(0/0),ct_zone(0/0),
    ct_mark(0/0),ct_label(0/0),recirc_id(0),dp_hash(0/0),in_port(net_jmnd1),packet_type(ns=0,id=0),
    eth(src=00:01:00:00:00:02/00:00:00:00:00:00,dst=04:02:03:04:05:06/00:00:00:00:00:00),eth_type(0x0800),
    ipv4(src=185.233.190.2,dst=172.0.1.1/0.0.0.0,proto=0/0,tos=0/0,ttl=64/0,frag=no), packets:15,
     bytes:510, dpe_packets:15, dpe_bytes:510,used:169.207s, offloaded:yes, dp:dpdk,
     actions:net_jmnd2, dp-extra-info:miniflow_bits(4,2)

 ufid:2fc206e0-1efc-4e6d-ac65-e430bff08ad4, skb_priority(0/0),skb_mark(0/0),ct_state(0/0),ct_zone(0/0),ct_mark(0/0),ct_label(0/0),recirc_id(0),dp_hash(0/0),in_port(net4),packet_type(ns=0,id=0),eth(src=00:01:00:00:00:02/00:00:00:00:0
0:00,dst=04:02:03:04:05:06/00:00:00:00:00:00),eth_type(0x0800),ipv4(src=185.233.190.2,dst=172.0.1.1/0.0.0.0,proto=0/0,tos=0/0,ttl=64/0,frag=no), packets:0, bytes:0, dpe_packets:0, dpe_bytes:0,used:never, offloaded:yes, dp:dpdk, acti
ons:net5, dp-extra-info:miniflow_bits(4,2)

    """
    cmd = f'ovs-appctl dpctl/dump-flows -m |grep offloaded:yes |grep -v drop'
    result = n2_session.execute_command(cmd)
    # flow_lines = result.strip().replace('\n', '')
    flow_lines = result.strip().split('\n')

    logging.info(f"-----------------------------execute_command({cmd}):\n {result}")

    flag1 = f'in_port({in_port})'
    flag3 = f'actions:{output}'

    logging.info(f"-----------------------------flag1={flag1} flag3={flag3}\n")
    dpe_packets_num = 0
    for line in flow_lines:
        if (flag1 in line) and (flag3 in line):
            # dpe_packets_num = re.findall(r'dpe_packets:(\d+)', line)
            dpe_packets_num = re.findall(r'packets:(\d+)', line)
            break
        # else:
        #     raise Exception('错误：没有找到对应的流表')
    return dpe_packets_num
