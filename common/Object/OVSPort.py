class OVSPort:
    def __init__(self, bridge_name, port_name, interface_name, port_type, options):
        self._bridge_name = bridge_name
        self._port_name = port_name
        self._interface_name = interface_name
        self._port_type = port_type
        self._options = options

    @property
    def bridge_name(self):
        return self._bridge_name

    @property
    def port_name(self):
        return self._port_name

    @property
    def interface_name(self):
        return self._interface_name

    @property
    def port_type(self):
        return self._port_type

    @property
    def options(self):
        return self._options


    def __str__(self):
        return (
            f"Bridge Name: {self.bridge_name}\n"
            f"Port Name: {self.port_name}\n"
            f"Interface Name: {self.interface_name}\n"
            f"Port Type: {self.port_type}\n"
            f"Options: {self.options}\n"
        )




def main():
    # 示例数据
    bridge_name = "br-ext"
    port_name = "vnet1"
    interface_name = "vnet1"
    port_type = "dpdk"
    options = {
        "dpdk-devargs": "net_virtio_user1,path=/dev/vhost-vdpa-2,queues=1,queue_size=512,is_va=1"
    }

    # 创建一个实例
    ovs_port = OVSPort(bridge_name, port_name, interface_name, port_type, options)



    # 打印OVS端口信息
    print(ovs_port)

if __name__ == '__main__':
    main()