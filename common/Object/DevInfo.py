class DevInfo:
    def __init__(self):
        self.ens_name = None
        self.pcie_num = None
        self.bdf_num = None
        self.jmnd_dev_name = None
        self.source_path = None
        self.dpdk_port_name = None
        self.mac_addr = None

    def __init__(self, ens_name):
        self.ens_name = ens_name
        self.pcie_num = None
        self.bdf_num = None
        self.jmnd_dev_name = None
        self.source_path = None
        self.dpdk_port_name = None
        self.mac_addr = None

    def set_property(self, property_name, value):
        # 检查属性名是否有效
        if hasattr(self, property_name):
            setattr(self, property_name, value)
        else:
            print(f"Error: Property '{property_name}' does not exist.")


def main():
    # 示例用法
    device_instance = DevInfo()

    # 逐步设置属性
    device_instance.set_property('ens_name', 'ens0')
    device_instance.set_property('pcie_num', '0000:01:00.0')
    # ... 逐步设置其他属性

    # 访问属性
    print("Device Name:", device_instance.jmnd_dev_name)
    print("PCIe Num:", device_instance.pcie_num)
    # ... 可以访问其他属性


if __name__ == '__main__':
    main()
