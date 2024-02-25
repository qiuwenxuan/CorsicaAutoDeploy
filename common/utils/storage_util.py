import logging
import os
import time
import re

from common.base_common import sftp_util
from common.utils.util import subprocess_command


def scp_fio_cfg_to_host(it_session):
    """
    fio配置文件的拷贝,先scp拷贝模版配置文件到host侧
    """
    SIMConfPage = it_session.get_configure()
    host_server = SIMConfPage.get_host_server()
    # host = host_server.hostname
    # port = 6013
    # username = 'root'
    # password = 'root'

    parent_dir = os.path.dirname(os.path.abspath(__file__))
    local_file_path = f"{parent_dir}/../../config/fio_test.cfg"
    logging.info(f"host_server:{host_server.hostname},{host_server.username},{host_server.password},{host_server.port}")
    remote_directory = '/root/'
    logging.info(f"local_file_path={local_file_path},remote_directory={remote_directory}")

    sftp = sftp_util.SftpUtil(host_server.hostname, host_server.username, host_server.password, int(host_server.port))
    sftp.open()
    sftp.upload_file_sftp(local_file_path, remote_directory)
    sftp.close()


def complete_fio_cfg(host_session, dev_list):
    """
    根据实际环境的传入的dev设备列表，配置job name及filename
    """

    str_dev = ''
    if not isinstance(dev_list, list):
        dev_list = [dev_list]
    # dict_keys(['vda'])
    for i in dev_list:
        str1 = "[fio-test-%s]\n" % i
        str2 = "filename=/dev/%s\n" % i
        str_dev = str_dev + str1 + str2
    logging.info(f"\n-----------------------------str_dev:\n {str_dev}")

    host_session.execute_command("echo '%s' >> /root/fio_test.cfg" % str_dev)


def kill_fio_process(host_session):
    """
    kill掉fio进程，并做检查，是否真的kill掉，无法kill掉fio进程时，则判断出错
    作用一：先清理环境，为新的fio测试做准备；
    作用二：提前终止fio测试，提前结束fio测试。
    """
    cmd_kill = "ps aux |grep 'fio /root/fio_test.cfg --eta-newline=1 --output=/root/fio_test_output.txt'|grep -v grep \
          | awk '{print $2}' |xargs kill -15"
    logging.info(f"\n-----------------------------kill掉fio进程的具体命令为:\n {cmd_kill}")

    cmd_check = "ps aux |grep 'fio /root/fio_test.cfg --eta-newline=1 --output=/root/fio_test_output.txt'|grep -v grep \
          | awk '{print $2}'"
    logging.info(f"\n-----------------------------查询fio进程号的具体命令为:\n {cmd_check}")
    for i in range(300):
        host_session.execute_command(f"{cmd_kill}")
        result = host_session.execute_command(f'{cmd_check}')
        if len(result) == 0:
            break
        time.sleep(2)
    if i > 300:
        result == "", "fio进程无法kill掉，需要排查"
    return result


def run_fio(host_session, ioengine='libaio', iodepth=64, numjobs=1, bsrange='4k-4k', rw='randrw',
            rwmixread=50, runtime=3600, verify='crc32'):
    """
    fio启动，根据传入参数执行fio测试
    参考命令如下：
    cmd = 'tmux kill-session -t tmux_fio_test;tmux new -s tmux_fio_test -d && tmux send -t tmux_fio_test
    "IOENGINE=libaio IODEPTH=16 NUMJOBS=1 BSRANGE=512B-1024k RW=randrw RWMIXREAD=10 RUNTIME=300 VERIFY=crc32
    fio /root/fio_test.cfg --eta-newline=1 --output=/root/fio_test_output.txt" Enter'
    """
    cmd = 'tmux kill-session -t tmux_fio_test;tmux new -s tmux_fio_test -d -x 100&& tmux send -t tmux_fio_test \
    "IOENGINE={fio_ioengine} IODEPTH={fio_iodepth} NUMJOBS={fio_numjobs} BSRANGE={fio_bsrange} RW={fio_rw} \
    RWMIXREAD={fio_rwmixread} RUNTIME={fio_runtime} VERIFY={fio_verify} fio /root/fio_test.cfg --eta-newline=1 \
    --output=/root/fio_test_output.txt" Enter'.format(fio_ioengine=ioengine, fio_iodepth=iodepth, fio_numjobs=numjobs,
                                                      fio_bsrange=bsrange, fio_rw=rw, fio_rwmixread=rwmixread,
                                                      fio_runtime=runtime, fio_verify=verify)
    logging.info(f"\n-----------------------------fio run的具体命令为:\n {cmd}")
    host_session.execute_command(f"{cmd}")


def get_result_of_fio(host_session):
    """
    获取fio测试的实时结果，如下所示：
    Jobs: 2 (f=2): [V(1),M(1)][10.8%][r=35.7MiB/s,w=18.0MiB/s][r=9136,w=4613 IOPS][eta 00m:58s]
    """
    cmd = 'tmux capture-pane -S -20 -t tmux_fio_test && tmux show-buffer'
    output = host_session.execute_command(f"{cmd}")
    output = output.strip()
    realtime_output = output.split('\n')[-1]
    logging.info(f"\n-----------------------------实时fio最后一行输出为:\n {realtime_output}")
    result = re.findall(r'IOPS]', realtime_output)
    # assert len(result) != 0, "实时fio结果中没有IOPS值，需要排查"
    if len(result) != 0:
        return True
    else:
        return False


def get_real_time_result_of_fio(host_session):
    """
    获取fio测试的实时结果，如下所示：
    Jobs: 2 (f=2): [V(1),M(1)][10.8%][r=35.7MiB/s,w=18.0MiB/s][r=9136,w=4613 IOPS][eta 00m:58s]
    """
    cmd = 'tmux capture-pane -S -20 -t tmux_fio_test && tmux show-buffer'
    output = host_session.execute_command(f"{cmd}")
    output = output.strip()
    realtime_output = output.split('\n')[-1]
    logging.info(f"\n-----------------------------实时fio最后一行输出为:\n {realtime_output}")
    result = re.findall(r'IOPS]', realtime_output)
    assert len(result) != 0, "实时fio结果中没有IOPS值，需要排查"


def get_final_result_of_fio(host_session):
    """
    获取fio测试的最终结果，查看是否有IO error、failed等打印，查看IOPS值等
    """
    cmd = 'cat /root/fio_test_output.txt'
    finally_output = host_session.execute_command(f"{cmd}")
    logging.info(f"\n-----------------------------最终的fio测试结果输出为:\n {finally_output}")
    result1 = re.findall(r'error', finally_output)
    assert len(result1) == 0, "fio测试结果中出现IO error，需要排查"
    result2 = re.findall(r'failed', finally_output)
    assert len(result2) == 0, "fio测试结果中出现IO failed，需要排查"
    result3 = re.findall(r'IOPS=(\d+)', finally_output)
    assert len(result3) != 0, "fio测试结果中没有IOPS值，需要排查"


def check_vhost(n2_session):
    # 检查vhost进程是否存在
    cmd = "ps aux |grep 'jmnd_vhost'|grep -v grep| awk '{print $2}' |wc -l"
    vhost_num = n2_session.execute_command(f"{cmd}")
    return vhost_num


def get_vhost_log(n2_session):
    cmd = "tail -10 /var/log/jmnd/start_jmnd_vhost.log"
    result = n2_session.execute_command(f"{cmd}")
    # logging.info(f"\n-----------------------------log result输出为:\n {result}")
    return result


def kill_vhost(n2_session):
    # N2杀掉vhost进程
    cmd = "ps aux |grep 'jmnd_vhost'|grep -v grep| awk '{print $2}' |xargs kill -9"
    n2_session.execute_command(f"{cmd}")

    timeout = 30
    start_time = time.time()

    while True:
        current_time = time.time()
        elapsed_time = current_time - start_time

        if elapsed_time > timeout:
            logging.error("超时：vhost进程未被kill掉")
            break

        # 获取vhost进程数
        result = check_vhost(n2_session)

        if result == "":
            logging.info("vhost进程已被kill掉")
            break

        # 间隔10秒再次获取实时结果
        time.sleep(2)


def start_vhost(n2_session, dev_type, num):
    cmd = "/usr/share/jmnd/single/debug_script/com/start_spdk.sh"
    output = n2_session.execute_command(f"{cmd}")

    logging.info(f"------------------------------重启spdk：\n{output}")
    timeout = 30
    start_time = time.time()

    while True:
        current_time = time.time()
        elapsed_time = current_time - start_time

        if elapsed_time > timeout:
            logging.error("超时：vhost进程未启动成功")
            break

        # 获取vhost进程数
        result = check_vhost(n2_session)

        if int(result) == 1:
            logging.info("vhost进程已启动成功")
            break

        # 间隔10秒再次获取实时结果
        time.sleep(2)

    find_string = ''
    if dev_type == "blk":
        num = num + 1
        find_string = f"/var/tmp/vhost.{num}"
        logging.info(f"\n-----------------------------find_string:\n {find_string}")
    elif dev_type == "nvme":
        num = num - 1
        find_string = f"/var/tmp/vnvme.{num}"
        logging.info(f"\n-----------------------------find_string:\n {find_string}")

    timeout = 1200
    start_time = time.time()
    while True:
        current_time = time.time()
        elapsed_time = current_time - start_time

        if elapsed_time > timeout:
            logging.error("超时：vhost进程未启动成功")
            break

        # 获取vhost进程数
        result = get_vhost_log(n2_session)
        lines = result.strip().split('\n')
        for line in lines:
            if find_string in line:
                logging.info("vhost进程已启动成功")
            break
        logging.info(f"\n-----------------------------find_string:\n {result}")
        # 间隔10秒再次获取实时结果
        time.sleep(10)


def start_vhost_PX2(n2_session, dev_type, num):
    # 修改了cmd命令
    cmd = "cd /usr/share/jmnd/single/debug_script/8net_8blk;./3_start_spdk.sh"
    n2_session.execute_command(f"{cmd}")
    timeout = 30
    start_time = time.time()
    while True:
        current_time = time.time()
        elapsed_time = current_time - start_time

        if elapsed_time > timeout:
            logging.error("超时：vhost进程未启动成功")
            break

        # 获取vhost进程数
        result = check_vhost(n2_session)

        if int(result) == 1:
            logging.info("vhost进程已启动成功")
            break

        # 间隔10秒再次获取实时结果
        time.sleep(2)
    find_string = ''
    if dev_type == "blk":
        num = num + 1
        find_string = f"/var/tmp/vhost.{num}"
        logging.info(f"\n-----------------------------find_string:\n {find_string}")
    elif dev_type == "nvme":
        num = num - 1
        find_string = f"/var/tmp/vnvme.{num}"
        logging.info(f"\n-----------------------------find_string:\n {find_string}")

    timeout = 1200
    start_time = time.time()
    while True:
        current_time = time.time()
        elapsed_time = current_time - start_time

        if elapsed_time > timeout:
            logging.error("超时：vhost进程未启动成功")
            break

        # 获取vhost进程数
        result = get_vhost_log(n2_session)
        lines = result.strip().split('\n')
        for line in lines:
            if find_string in line:
                logging.info("vhost进程已启动成功")
            break

        # 间隔10秒再次获取实时结果
        time.sleep(2)


def reset_host(it_session, cmd, timeout=1200):
    # 1.在windows调试机上执行冷重启命令
    subprocess_command(cmd)

    # 2.获取host侧的ip地址
    ConfPage = it_session.get_configure()
    host_server = ConfPage.get_host_server()
    host_name = host_server.hostname

    # 3.拼接验证host端是否起的命令
    out_put = ''
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
    return True


# 加载virtio驱动时，需先关闭RC超时时间
def disable_rc_timeout(host_session):
    host_session.execute_command('setpci -s 3e:02.0 68.w=0099')
    out_put = host_session.execute_command('lspci -s 3e:02.0 -vvv |grep TimeoutDis')
    if 'TimeoutDis+' in out_put:
        return True
    return False
