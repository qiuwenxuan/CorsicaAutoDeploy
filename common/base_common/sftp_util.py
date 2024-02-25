import paramiko


class SftpUtil:
    def __init__(self, address, username, password, port=22):
        print("Connecting to server on ip", str(address) + ":" + str(port) + ".")
        self.address = address
        self.username = username
        self.password = password
        self.port = port
        self.transport = None

    def __del__(self):
        self.close()

    def open(self):
        try:
            self.transport = paramiko.Transport((self.address, self.port))
            self.transport.connect(username=self.username, password=self.password)
        except BaseException as e:
            print(e)
            return False
        return True

    def close(self):
        if self.transport is not None:
            self.transport.close()
            self.transport = None
            print('close transport')

    def upload_file_sftp(self, local_file_path, remote_directory):
        # try:
        #     # 创建SFTP客户端
        #     sftp = self.transport.open_sftp_client()
        #
        #     # 上传文件
        #     local_filename = local_file_path.split('/')[-1]  # 获取本地文件名
        #     remote_filepath = f"{remote_directory}/{local_filename}"
        #     sftp.put(local_file_path, remote_filepath)
        #
        #     sftp.close()
        #     return True
        # except Exception as e:
        #     print(f"文件上传失败：{e}")
        #     return False

        # 创建SFTP客户端
        try:
            sftp = self.transport.open_sftp_client()

            # 上传文件
            local_filename = local_file_path.split('/')[-1]  # 获取本地文件名
            remote_filepath = f"{remote_directory}/{local_filename}"
            sftp.put(local_file_path, remote_filepath)

            sftp.close()
        except Exception as e:
            raise Exception(f"下载文件时发生错误: {str(e)}")
            return False
        finally:
            sftp.close()
        return True

    def download_file_sftp(self, remote_file_name, local_file_path):
        try:
            sftp = self.transport.open_sftp_client()

            # 从远程服务器下载文件到本地
            sftp.get(remote_file_name, local_file_path)

            sftp.close()
        except Exception as e:
            raise Exception(f"下载文件时发生错误: {str(e)}")
            return False
        finally:
            sftp.close()

        return True



def main():
    remote_server = "10.20.69.58"
    remote_port = 6002
    remote_username = "root"
    remote_password = "root"
    remote_file_name = "/usr/share/jmnd/single/debug_script/2net_2blk/easy_bm.xml"
    local_file_path = "./easy_bm.xml"

    sftp = SftpUtil(remote_server, remote_username, remote_password, remote_port)
    sftp.open()
    sftp.download_file_sftp(remote_file_name, local_file_path)
    sftp.close()


if __name__ == '__main__':
    main()
