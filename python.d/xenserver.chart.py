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

CHART = {
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




class Service(SimpleService):
    session = None
    url = None
    username = None
    password = None


    def __init__(self, configuration=None, name=None):
        SimpleService.__init__(self, configuration, name)
        if self.configuration.get('url'):
            self.url = self.configuration['url']
            match = _uri_credentials.match(self.url)
            if match:
                self.username = match.group('user')
                self.password = match.group('pass')
                self.url = self.url.replace(match.group('credentials'), '')


    def _connect(self, force=False):
        '''Attempt to connect to a local XenServer API through :attr:`url`

        :param bool force: attempt a connection even if one seems present
        :return: a (hopefully active) XenAPI session
        :rtype: XenAPI.Session
        '''
        if not self.session or force:
            if self.url and (self.username or self.password):
                self.session = XenAPI.Session(self.url)
                self.session.login_with_password(
                    self.username or '',
                    self.password or '',
                )
            else:
                self.session = XenAPI.xapi_local()
        return self.session


    def check(self):
        if XenAPI is not None:
            try:
                return bool(self._connect())
            except:
                pass
        return False


    def _get_data(self):
        if not self.session:
            try:
                self._connect()
            except:
                return
        # TODO
