# -*- coding: utf-8 -*-

import os
import logging
import time

from common.base_common import sftp_util
from common.utils import ovs_flow


def scp_trex_cfg_yaml_to_trex_server(server_conf):
    """
    trex_cfg.yaml文件拷贝至测试机
    """
    # ConfPage = it_session.get_configure()
    # if type == "n2":
    #     trex_server = ConfPage.get_n2_server()
    # elif type == "host":
    #     trex_server = ConfPage.get_host_server()
    # else:
    #     raise Exception('The type is error,currently only n2 and host are supported')
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    local_file_path = f"{parent_dir}/../../config/trex_cfg.yaml"
    logging.info(
        f"trex_server:{server_conf.hostname},{server_conf.username},{server_conf.password},{server_conf.port}")
    remote_directory = '/etc/'
    logging.info(f"local_file_path={local_file_path},remote_directory={remote_directory}")

    sftp = sftp_util.SftpUtil(server_conf.hostname, server_conf.username, server_conf.password,
                              int(server_conf.port))
    sftp.open()
    sftp.upload_file_sftp(local_file_path, remote_directory)
    sftp.close()


def config_trex_cfg_yaml_on_trex_server(session, port1, port2):
    r"""
    根据实际测试的端口，修改trex_cfg.yaml文件
    sed -i '/interfaces\s*:\s*\[".*",".*"\]/s/["].*["],["].*["]/"{port1}","{port2}"/'
    /etc/trex_cfg.yaml
    """
    # if port1 == port2:
    #     raise Exception('错误：trex的0口和1口配置应不同')

    cmd = rf"""sed -i '/interfaces\s*:\s*\[".*",".*"\]/s/["].*["],["].*["]/"{port1}","{port2}"/' \
              /etc/trex_cfg.yaml"""
    session.execute_command(cmd)
    cmd1 = f'ifconfig {port1} up'
    cmd2 = f'ifconfig {port2} up'
    session.execute_command(cmd1)
    session.execute_command(cmd2)


def get_tmux_output(session, tmux_name, line_number):
    """
    获取指定tmux窗口的最后n行输出
    tmux capture-pane -S -10 -t tmux_tcpdump && tmux show-buffer
    """
    cmd = f'tmux capture-pane -S -{line_number} -t {tmux_name} && tmux show-buffer'
    result = session.execute_command(cmd)
    return result


def check_status_of_specific_cmd(session, tmux_name, cmd_name, flag, timeout=30):
    start_time = time.time()
    while True:
        current_time = time.time()
        elapsed_time = current_time - start_time

        if elapsed_time > timeout:
            logging.error(f"超时：{cmd_name}未启动成功")
            ret = False
            break

        # 获取tmux窗口打印
        result = get_tmux_output(session, tmux_name, 2)
        if flag in result:
            logging.info(f"{cmd_name}已启动成功")
            ret = True
            break

        # 间隔2秒再次获取tmux窗口打印
        time.sleep(2)
    return ret


def start_trex_server(session, timeout=30):
    """
    使用如下命令启动trex-server
    cd /home/v2.93/ && ./t-rex-64 -i --no-scapy-server
    开启tmux窗口执行该命令，执行命令后查看是否有current time，若有，则代表
    """
    cmd = 'tmux kill-session -t tmux_trex_server;tmux new -s tmux_trex_server -d && tmux send -t tmux_trex_server ' \
          '"cd /home/v2.93/ && ./t-rex-64 -i --no-scapy-server" Enter'
    result = session.execute_command(cmd)
    if result != '':
        # not与逻辑判断句if连用，代表not后面的表达式为False的时候，执行冒号后面的语句
        logging.error(f"execute_command fail.cmd={cmd}")
        return False
    result = check_status_of_specific_cmd(session, "tmux_trex_server", "trex-server", "current time", timeout)
    logging.info(f"execute_command successed.cmd={cmd}")
    return result


def start_trex_console(session, timeout=30):
    """
    使用如下命令启动trex-console
    cd /home/v2.93/ && ./trex-console -r
    """
    cmd = 'tmux kill-session -t tmux_trex_console;tmux new -s tmux_trex_console -d && tmux send -t tmux_trex_console ' \
          '"cd /home/v2.93/ && ./trex-console -r" Enter'
    result = session.execute_command(cmd)
    if result != '':
        # not与逻辑判断句if连用，代表not后面的表达式为False的时候，执行冒号后面的语句
        logging.error(f"execute_command fail.cmd={cmd}")
        return False

    result = check_status_of_specific_cmd(session, "tmux_trex_console", "trex-console", "trex(read-only)>",timeout)
    return result


def send_packet_on_trex_console(session, port):
    """
    在trex-console终端从0口发1个包，其源IP地址为185.233.190.2
    pkt -p 0 -s Ether(dst='04:02:03:04:05:06',src='00:01:00:00:00:02')/IP(src='185.233.190.2',dst='172.0.1.1')
    """
    cmd = f"""tmux send -t tmux_trex_console "pkt -p {port} -s Ether(dst='04:02:03:04:05:06',src='00:01:00:00:00:02')/\
IP(src='185.233.190.2',dst='172.0.1.1')" Enter"""
    result = session.execute_command(cmd)
    if result != '':
        # not与逻辑判断句if连用，代表not后面的表达式为False的时候，执行冒号后面的语句
        logging.error(f"execute_command fail.cmd={cmd}")
        return False
    return True


def start_tcpdump(session, port, src, dump_num=2):
    """
    tcpdump抓指定端口、指定源地址的一个包，获取到一个后立即停止抓包
    """
    cmd = f'tmux kill-session -t tmux_tcpdump;tmux new -s tmux_tcpdump -d && tmux send -t tmux_tcpdump ' \
          f'"tcpdump -i {port} -c {dump_num} -xxx src {src}" Enter'
    result = session.execute_command(cmd)
    if result != '':
        # not与逻辑判断句if连用，代表not后面的表达式为False的时候，执行冒号后面的语句
        logging.error(f"execute_command fail.cmd={cmd}")
        return False

    result = check_status_of_specific_cmd(session, "tmux_tcpdump", "tcpdump", "listening on")
    return result


def start_tmux_tcpdump(session, port, src):
    """
    tcpdump抓指定端口、指定源地址的一个包，获取到一个后立即停止抓包
    """
    cmd = f'tmux kill-session -t tmux_tcpdump;tmux new -s tmux_tcpdump -d && tmux send -t tmux_tcpdump ' \
          f'"tcpdump -i {port} -c 1 -xxx src {src}" Enter'
    result = session.execute_command(cmd)
    if not result:
        # not与逻辑判断句if连用，代表not后面的表达式为False的时候，执行冒号后面的语句
        logging.error(f"execute_command fail.cmd={cmd}")
        return False

    result = check_status_of_specific_cmd(session, "tmux_tcpdump", "tcpdump", "listening on")
    if not result:
        # not与逻辑判断句if连用，代表not后面的表达式为False的时候，执行冒号后面的语句
        logging.error(f"check_status_of_specific_cmd fail.")
        return False

    return result


def count_timestamps(dump_result: str, src):
    """ 读取tcpdump输出文件的第一个时间戳 """
    lines = dump_result.split('\n')
    num: int = 0
    for line in lines:
        if f"IP {src}" in line:
            num = num + 1
    return num


def check_tcpdump_result(session, src, times=1, timeout=30):
    """
    获取tcpdump的结果，预期会抓到一个包
    """
    start_time = time.time()
    while True:
        result = get_tmux_output(session, "tmux_tcpdump", 10)
        logging.info(f"\n result:\n {result}")

        count_tamps = count_timestamps(result, src)
        # 检查是否满足条件
        if count_tamps == times:
            result = True
            break
        # 检查是否超时（30秒）
        if time.time() - start_time > timeout:
            result = False
            break

        # 等待2秒再次检查
        time.sleep(2)
    return result


def trex_send_one_packet_and_check(tcpdump_session, tcpdump_port, trex_session, src, n2_session,
                                   ovs_inport, ovs_output, expect_num):
    # 发包前先启动tcpdump抓包命令
    start_tcpdump_one_packet(tcpdump_session, tcpdump_port, src)
    # trex从0口发一个包
    send_one_packet_on_trex_console(trex_session, 0)
    # 查看tcpdump抓包结果
    result = check_tcpdump_result(tcpdump_session, src)
    assert result
    # 查看流表计数
    for i in range(10):
        num = ovs_flow.get_flow_packets(n2_session, ovs_inport, src, ovs_output)
        if int(num[0]) == expect_num:
            break
        elif int(num[0]) != expect_num and i == 9:
            raise Exception(f'错误：流表计数不为{expect_num}！')
    num = ovs_flow.get_offload_flow_packets(n2_session, ovs_inport, src, ovs_output)
    offload_expect_num = expect_num - 1
    if int(num[0]) != offload_expect_num:
        raise Exception(f'错误：卸载流表计数不为{offload_expect_num}！')
