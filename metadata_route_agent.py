#! -*- coding: utf8 -*-
import sys, time
import subprocess
from quantum.agent.common import config
from quantum.openstack.common import cfg
from quantum.openstack.common import log as logging
from quantumclient.v2_0 import client

LOG = logging.getLogger(__name__)

class MetadataRouteAgent(object):

    OPTS = [
        cfg.StrOpt('admin_user'),
        cfg.StrOpt('admin_password'),
        cfg.StrOpt('admin_tenant_name'),
        cfg.StrOpt('auth_url'),
        cfg.StrOpt('auth_strategy', default='keystone'),
        cfg.StrOpt('auth_region'),
        cfg.StrOpt('root_helper', default='sudo'),
        cfg.IntOpt('polling_interval',
                   default=3,
                   help="The time in seconds between state poll requests."),
    ]

    def __init__(self, conf):
        self.conf = conf
        self.router_info = {}

        self.polling_interval = conf.polling_interval

        self.qclient = client.Client(
            username=self.conf.admin_user,
            password=self.conf.admin_password,
            tenant_name=self.conf.admin_tenant_name,
            auth_url=self.conf.auth_url,
            auth_strategy=self.conf.auth_strategy,
            auth_region=self.conf.auth_region
        )

    def daemon_loop(self):
        while True:
            try:
                self.do_single_loop()
            except:
                LOG.exception("Error running metadata_route daemon_loop")

            time.sleep(self.polling_interval)

    def do_single_loop(self):
        routers = self.qclient.list_routers()['routers'];
        ports = self.qclient.list_ports()

        route_info = []
        for r in routers:
            # get tenant's subnet
            subnet = self.qclient.list_ports(device_id=r['id'],
                    device_owner='network:router_interface')['ports'][0]['fixed_ips'][0]['subnet_id']
            cidr = self.qclient.show_subnet(subnet=subnet)['subnet']['cidr']

            # get the tenant's gw
            fixed_ip = self.qclient.list_ports(device_id=r['id'],
                    device_owner='network:router_gateway')['ports'][0]['fixed_ips'][0]['ip_address']
            route_info.append((cidr, fixed_ip))

        # get current route info
        old_routes = [x.split() for x in subprocess.check_output(['ip', 'route']).splitlines()[2:] if ('via' in x and 'default' not in x) ]
        old_routes = [(x[0], x[2]) for x in old_routes]

        # add new routing info
        for cidr, fixed_ip in set(route_info) - set(old_routes):
            subprocess.check_call(['route', 'add', '-net', cidr, 'gw', fixed_ip])
        
        # remove routing info
        for cidr, fixed_ip in set(old_routes) - set(route_info):
            subprocess.check_call(['route', 'del', '-net', cidr, 'gw', fixed_ip])


def main():
    conf = config.setup_conf()
    conf.register_opts(MetadataRouteAgent.OPTS)
    conf(sys.argv)
    config.setup_logging(conf)

    mgr = MetadataRouteAgent(conf)
    mgr.daemon_loop()


if __name__ == '__main__':
    main()
