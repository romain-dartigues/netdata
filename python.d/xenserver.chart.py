#!/usr/bin/env python
# vim:set fileencoding=utf8 ts=4 sw=4 et:
'''
See: https://github.com/firehol/netdata/wiki/How-to-write-new-module

Sample configuration:

.. code-block:: yaml

   ---
   remote1:
     url: https://user:pass@example.net/
'''

# stdlib
import random
import re

# netdata dependency
from base import SimpleService

# Xen API Python modle
try:
    import XenAPI
except ImportError:
    XenAPI = None




priority = 90000
retries = 10
update_every = 60

_uri_credentials = re.compile(
    '^[a-z]*://(?P<credentials>(?P<user>[^:]*)(?:\:(?P<pass>[^@]*))?\@)'
)

ORDER = [
    'PIF_metrics',
    'VBD_metrics',
    'VIF_metrics',
    'VM_guest_metrics',
    'VM_metrics',
]

CHARTS = {
    'PIF_metrics': {
        'options': [None, 'Physical InterFaces', 'kiB/s', 'bandwidth', 'pif.metrics'],
        'lines': [
            ['io_read_kbs', 'Read bandwidth'],
            ['io_write_kbs', 'Write bandwidth'],
        ],
    },
    'VBD_metrics': {
        'options': [None, 'Virtual Block Device', 'kiB/s', 'bandwidth', 'vbd.metrics'],
        'lines': [
            ['io_read_kbs', 'Read bandwidth'],
            ['io_write_kbs', 'Write bandwidth'],
        ],
    },
    'VIF_metrics': {
        'options': [None, 'Virtual InterFaces', 'kiB/s', 'bandwidth', 'pif.metrics'],
        'lines': [
            ['io_read_kbs', 'Read bandwidth'],
            ['io_write_kbs', 'Write bandwidth'],
        ],
    },
    # http://docs.vmd.citrix.com/XenServer/6.5.0/1.0/en_gb/api/?c=VM_guest_metrics
    'VM_guest_metrics': {
        'options': [None, 'metrics reported by the guest', None, 'VM.guest', 'VM.guest.metrics', 'stacked'],
        'lines': [
            ['memory', 'free/used/total memory', None],
        ],
    },
    'VM_metrics_CPU': {
        'options': [None, "Guest VCPUs", 'number', 'VM', 'VM.metrics.CPU'],
        'lines': [
            ['VCPUs_number', "current number of VCPUs"],
            ['VCPUs_utilisation', "utilisation for all of guest's current VCPUs"],
        ],
    },
    'VM_metrics_mem': {
        'options': [None, "Guest actual's memory", 'bytes', 'VM', 'VM.metrics'],
        'lines': [
            ['memory_actual', "guest actual\'s memory"],
        ],
    },
}





#dbg_file = open('/tmp/rdartigues.log', 'w', 1)
dbg_file = __import__('sys').stdout
dbg = lambda s:(dbg_file.write('%s\n'%(s,)), dbg_file.flush())

class Service(SimpleService):
    session = None
    ''':class:`XenAPI.Session` instance
    '''

    url = None
    '''URL of the XenServer API (without credentials)
    '''

    username = ''
    '''username (extracted from the URI)
    '''

    password = ''
    '''password (extracted from the URI)
    '''

    def __init__(self, configuration=None, name=None):
        SimpleService.__init__(self, configuration, name)

        self.definitions = CHARTS
        self.order = sorted(CHARTS)

        if self.configuration.get('url'):
            self.url = self.configuration['url']
            match = _uri_credentials.match(self.url)
            if match:
                self.username = match.group('user')
                self.password = match.group('pass')
                self.url = self.url.replace(match.group('credentials'), '')


    def check(self):
        """
        Check if service is able to connect to server
        :return: boolean
        """
        dbg('xs: check...')
        return isinstance(self._connect(), XenAPI.Session)


#    def create(self):
#        dbg('xs: create!')
#        self.chart("example.python_random", '', 'A random number', 'random number',
#                   'random', 'random', 'line', self.priority, self.update_every)
#        self.dimension('random1')
#        self.commit()
#        return True


#    def update(self, interval):
#        dbg('xs: update')
#        self.begin("example.python_random", interval)
#        self.set("random1", random.randint(0, 100))
#        self.end()
#        self.commit()
#        return True


    def _connect(self, force=False):
        '''Attempt to connect to a local XenServer API through :attr:`url`

        :param bool force: attempt a connection even if one seems present
        :return: status connection
        :rtype: bool
        '''
        if XenAPI is None:
            return False

        if not isinstance(self.session, XenAPI.Session) or force:
            if self.url and (self.username or self.password):
                self.session = XenAPI.Session(self.url)
            else:
                self.session = XenAPI.xapi_local()

            self.session.login_with_password(
                self.username or '',
                self.password or '',
                '1.0',
                'netdata',
            )

        return isinstance(self.session, XenAPI.Session)


    def _get_data(self):
        """
        Get some data
        :rtype: dict or None
        """
        if not self._connect():
            return
        data = {}

        host_ref = self.session.xenapi.session.get_this_host(self.session._session)
        host = self.session.xenapi.host.get_record(host_ref)
        host['metrics'] = self.session.xenapi.host_metrics.get_record(host['metrics'])

        # self.session.xenapi.SR.get_all_records()

#        VMs = self.session.xenapi.VM.get_all_records()
        VMs = self.session.xenapi.VM.get_all_records_where(
            'field "resident_on" = "%s"' % ( # and field "is_control_domain" = "false"
                host_ref,
            )
        )

        for VM in VMs:
            VM['metrics'] = self.session.xenapi.VM_metrics.get_record(VM['metrics'])

            if not VM['is_control_domain']:
                VM['VDIs'] = (
                    self.get_domU_VDIs_from_name(VM['name_label'])
                    or
                    self.get_domU_VDIs_from_conf(VM['name_label'])
                )

#        VM_metrics = self.session.xenapi.VM_metrics.get_all_records()

        return data





if __name__ == '__main__':
    self = Service({'update_every':3, 'priority':99999, 'retries':3})
    self.check()
