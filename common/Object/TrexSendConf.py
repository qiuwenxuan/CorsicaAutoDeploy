
class TrexInPort(object):
    port_name: str
    port_type: str
    ovs_tap: str
    src_ip: str

    def __init__(self, port_name, port_type, ovs_tap, src_ip=''):
        self.port_name = port_name
        self.port_type = port_type
        self.ovs_tap = ovs_tap
        self.src_ip = src_ip


class TrexOutPort(object):
    port_name: str
    port_type: str
    ovs_tap: str
    dst_ip: str

    def __init__(self, port_name, port_type, ovs_tap, dst_ip=''):
        self.port_name = port_name
        self.port_type = port_type
        self.ovs_tap = ovs_tap
        self.dst_ip = dst_ip


class TrexSendConf:
    inport: TrexInPort
    outport: TrexOutPort

    def __init__(self, inport, outport):
        self.inport = inport
        self.outport = outport
