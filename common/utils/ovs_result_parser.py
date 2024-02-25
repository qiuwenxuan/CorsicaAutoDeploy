import logging
import re

from common.Object.OVSPort import OVSPort


class OVSPortParser:
    def __init__(self, ovs_show_output):
        self.ovs_show_output = ovs_show_output
        self.ports = []

    def parse(self):
        # Initialize variables to track current context
        current_bridge = None
        current_port = None
        current_interface = None
        current_type = None
        current_options = {}

        # Regular expressions to match different parts of the output
        bridge_regex = re.compile(r'^Bridge (\w+)')
        port_regex = re.compile(r'^\s+Port (\w+)$')
        interface_regex = re.compile(r'^\s+Interface (\w+)$')
        type_regex = re.compile(r'^\s+type: (\w+)$')
        options_regex = re.compile(r'^\s+options: {(.+)}$')

        # Split the output into lines
        lines = self.ovs_show_output.split('\n')

        # Iterate through each line
        for line in lines:
            bridge_match = bridge_regex.match(line)
            port_match = port_regex.match(line)
            interface_match = interface_regex.match(line)
            type_match = type_regex.match(line)
            options_match = options_regex.match(line)

            if bridge_match:
                current_bridge = bridge_match.group(1)
            elif port_match:
                current_port = port_match.group(1)
            elif interface_match:
                current_interface = interface_match.group(1)
            elif type_match:
                current_type = type_match.group(1)
            elif options_match:
                # Parse the options string into a dictionary
                options_str = options_match.group(1)
                options = {}
                for option in options_str.split(','):
                    key, value = option.split('=')
                    options[key.strip()] = value.strip().replace('"', '')

                current_options = options

                ovs_port = OVSPort(current_bridge, current_port, current_interface, current_type, current_options)

                self.ports.append(ovs_port)

    def print_ports(self):
        ovs_port = []
        for port in self.ports:
            # print(port)
            ovs_port.append(port)
        return ovs_port


if __name__ == '__main__':
    ovs_show_output = """
    21fa56f9-fec3-45bd-9baf-db307ccc7fef
        Bridge br-ext
            fail_mode: standalone
            datapath_type: netdev
            Port vnet1
                Interface vnet1
                    type: dpdk
                    options: {dpdk-devargs="net_virtio_user1,path=/dev/vhost-vdpa-2,queues=1,queue_size=512,is_va=1"}
            Port br-ext
                Interface br-ext
                    type: internal
            Port net_jmnd2
                Interface net_jmnd2
                    type: dpdk
                    options: {dpdk-devargs="eth_jmnd2,iface=/tmp/sock1,client=1,queues=4", n_rxq="4"}
            Port net_jmnd1
                Interface net_jmnd1
                    type: dpdk
                    options: {dpdk-devargs="eth_jmnd1,iface=/tmp/sock0,client=1,queues=4", n_rxq="4"}
            Port vnet0
                Interface vnet0
                    type: dpdk
                    options: {dpdk-devargs="net_virtio_user0,path=/dev/vhost-vdpa-1,queues=1,queue_size=512,is_va=1"}
    """

    # Create an instance of OVSParser and parse the output
    parser = OVSPortParser(ovs_show_output)
    parser.parse()

    # Print the parsed port information
    parser.print_ports()
