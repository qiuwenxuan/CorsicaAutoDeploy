import logging
import os
from os.path import abspath


class DiskXMLGenerator:
    # 定义设备名称与vhost的映射
    dev_path_dicts = {
        'vda': 'vhost.2', 'vdb': 'vhost.3', 'vdc': 'vhost.4',
        'vdd': 'vhost.5', 'vde': 'vhost.6', 'vdf': 'vhost.7',
        'vdg': 'vhost.8', 'vdh': 'vhost.9', 'vdj': 'vhost.10'
    }
    xml_template = """<disk type='vhostuser' device='disk' model='virtio-transitional'>
      <driver name='qemu' type='raw' queues='4'/>
      <source type='unix' path='/var/tmp/{vhost_value}'>
        <reconnect enabled='yes' timeout='10'/>
      </source>
      <target dev='{blk_dev}' bus='virtio'/>
    </disk>\n"""

    # 创建disk.xml文件类方法
    @classmethod
    def create_disk_xml(cls, blk_devs, file_path='../../tmp'):
        xml_content = ''
        # 确保blk_devs是一个列表
        if not isinstance(blk_devs, list):
            blk_devs = [blk_devs]
        file_name = 'disk.xml'

        # 拼接完整本地disk.xml文件绝对文路径
        # full_file_path = os.path.abspath(os.path.join(file_path, file_name))
        # print(full_file_path)

        parent_dir = os.path.dirname(os.path.abspath(__file__))
        full_file_path = f"{parent_dir}/{file_path}/{file_name}"
        logging.info(f"\n----------------------------本地disk.xml文件路径full_file_path: {full_file_path}")
        for blk_dev in blk_devs:
            # 获取对应的vhost值
            vhost_value = cls.dev_path_dicts.get(blk_dev, '')

            # 使用模板生成特定的XML字符串
            xml_content += cls.xml_template.format(vhost_value=vhost_value, blk_dev=blk_dev)

        # 写入到文件
        with open(full_file_path, 'w') as file:
            file.write(xml_content)
        logging.info(f"\n----------------------------disk.xml:\n {xml_content}")
        return file_name


if __name__ == '__main__':
    # 使用示例
    blk_dev_list = ['vda', 'vdb', 'vdc', 'vde', 'vdf', 'vdg', 'vdh', 'vdj']
    DiskXMLGenerator.create_disk_xml(blk_dev_list)
