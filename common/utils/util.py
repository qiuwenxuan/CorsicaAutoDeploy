import logging
import os
import subprocess

from common.base_common import sftp_util

from common.utils.exception import TYPEError, Error


def scp_file_to_n2(it_session, file_name):
    ConfPage = it_session.get_configure()
    n2_server = ConfPage.get_n2_server()

    parent_dir = os.path.dirname(os.path.abspath(__file__))
    local_file_path = f"{parent_dir}/../../tmp/{file_name}"
    logging.info(f"n2_server:{n2_server.hostname},{n2_server.username},{n2_server.password},{n2_server.port}")
    remote_directory = '/root/'
    logging.info(f"local_file_path={local_file_path},remote_directory={remote_directory}")

    sftp = sftp_util.SftpUtil(n2_server.hostname, n2_server.username, n2_server.password, int(n2_server.port))
    sftp.open()
    sftp.upload_file_sftp(local_file_path, remote_directory)
    sftp.close()


def download_file_from_n2(it_session, remote_file):
    ConfPage = it_session.get_configure()
    n2_server = ConfPage.get_n2_server()
    logging.info(f"n2_server:{n2_server.hostname},{n2_server.username},{n2_server.password},{n2_server.port}")

    parent_dir = os.path.dirname(os.path.abspath(__file__))
    file_name = remote_file.split("/")[-1]
    local_file_path = f"{parent_dir}/../../tmp/{file_name}"
    logging.info(f"local_file_path={local_file_path},remote_file={remote_file}")
    sftp = sftp_util.SftpUtil(n2_server.hostname, n2_server.username, n2_server.password, int(n2_server.port))
    sftp.open()
    sftp.download_file_sftp(remote_file, local_file_path)

    sftp.close()
    return local_file_path


def subprocess_command(cmd):
    #  stdout=subprocess.PIPE, stderr=subprocess.PIPE以便捕获命令的标准输出和标准错误输出
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    outinfo, errinfo = process.communicate()
    if len(errinfo) != 0:
        logging.error("cmd执行出错，请排查")
        raise Error("cmd执行出错，请排查")
    logging.info(f"outinfo-----------:{outinfo.decode('gbk')}") # gbk解码输出结果信息
    logging.info(f"errinfo-----------:{errinfo.decode('gbk')}")
    return outinfo
