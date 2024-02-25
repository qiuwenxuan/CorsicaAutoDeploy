import xml.etree.ElementTree as ET

Jmnd_file_path = "./config/easy_bm.xml"


class EasyBmParser:
    def __init__(self, xml_file):
        self.tree = ET.parse(xml_file)
        self.root = self.tree.getroot()

    def get_name(self):
        return self.root.find('name').text

    def get_uuid(self):
        return self.root.find('uuid').text

    def get_interfaces(self):
        interfaces = []
        for interface_elem in self.root.findall(".//interface"):
            interface_info = {
                "mac_address": interface_elem.find('mac').get('address'),
                "model": interface_elem.find('model').get('type'),
                "driver_queues": interface_elem.find('driver').get('queues'),
                "source_path": interface_elem.find('source').get('path')
            }
            interfaces.append(interface_info)
        return interfaces

    def get_disks(self):
        disks = []
        for disk_elem in self.root.findall(".//disk"): # disk_elem提取了xml文件内所有的<disk>元素
            disk_info = {
                "type": disk_elem.get('type'),
                "device": disk_elem.get('device'),
                "model": disk_elem.get('model'),
                "driver_name": disk_elem.find('driver').get('name'),
                "driver_type": disk_elem.find('driver').get('type'),
                "driver_queues": disk_elem.find('driver').get('queues'),
                "source_path": disk_elem.find('source').get('path'),
                "target_dev": disk_elem.find('target').get('dev'),
                "target_bus": disk_elem.find('target').get('bus')
            }
            disks.append(disk_info)
        return disks

    def get_qemu_commandline(self):
        cmdline_elem = self.root.find(".//qemu:commandline",
                                      namespaces={'qemu': 'http://libvirt.org/schemas/domain/qemu/1.0'})
        args = [arg_elem.get('value') for arg_elem in
                cmdline_elem.findall('.//qemu:arg', namespaces={'qemu': 'http://libvirt.org/schemas/domain/qemu/1.0'})]
        return args

def main():
    # 示例用法
    domain_parser = EasyBmParser(Jmnd_file_path)

    print("Name:", domain_parser.get_name())
    print("UUID:", domain_parser.get_uuid())

    print("\nInterfaces:")
    interfaces = domain_parser.get_interfaces()
    for interface in interfaces:
        print(interface)

    print("\nDisks:")
    disks = domain_parser.get_disks()
    for disk in disks:
        print(disk)

    print("\nQEMU Commandline Args:")
    qemu_args = domain_parser.get_qemu_commandline()
    for arg in qemu_args:
        print(arg)

if __name__ == '__main__':
    main()



