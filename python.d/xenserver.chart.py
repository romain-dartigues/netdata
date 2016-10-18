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
import logging
import re

# netdata dependency
from base import SimpleService

# Xen API Python modle
try:
    import XenAPI
except ImportError:
    XenAPI = None




logging.basicConfig(
    filename='/tmp/rdartigues.log',
    format='%(asctime)s %(filename)s:%(lineno)d [%(levelname)s] %(message)s',
    datefmt='%FT%T',
    level=logging.DEBUG,
)
logger = logging.getLogger('netdata.xenserver')
logger.debug('module loaded')

priority = 90000
retries = 10
update_every = 1

_B2KiB = 1024
'''bytes to kibibyte'''

_B2MiB = 1024*1024
'''bytes to mebibyte'''

_B2GiB = 1024*1024*1024
'''bytes to gibibyte'''

_uri_credentials = re.compile(
    r'^[a-z]*://(?P<credentials>(?P<user>[^:]*)(?:\:(?P<pass>[^@]*))?\@)'
)

#ORDER = [
#    'PIF_metrics',
#    'VBD_metrics',
#    'VIF_metrics',
#    'VM_guest_metrics',
#    'VM_metrics',
#]

CHARTS = {
    'host': {
        'options': [None, "Host memory usage", "MB", 'mem', 'host.metrics', 'stacked'],
        'lines': [
            ['host.metrics.memory_free', 'free', 'absolute', 1, _B2MiB],
            ['host.metrics.memory_used', 'used', 'absolute', 1, _B2MiB],
        ],
    },
    'VMs.mem': {
        'options': [None, "VM memory usage", "MB", 'mem', 'vm.metrics', 'stacked'],
        'lines': [
            # set by Service.__get_VMs
        ],
    },
    'VMs.cpu': {
        'options': [None, 'VM CPU count', 'count', 'CPU', 'vm.metrics', 'line'],
        'lines': [
            # set by Service.__get_VMs
        ],
    },
#    'PIF_metrics': {
#        'options': [None, 'Physical InterFaces', 'kiB/s', 'bandwidth', 'pif.metrics'],
#        'lines': [
#            ['io_read_kbs', 'Read bandwidth'],
#            ['io_write_kbs', 'Write bandwidth'],
#        ],
#    },
#    'VBD_metrics': {
#        'options': [None, 'Virtual Block Device', 'kiB/s', 'bandwidth', 'vbd.metrics'],
#        'lines': [
#            ['io_read_kbs', 'Read bandwidth'],
#            ['io_write_kbs', 'Write bandwidth'],
#        ],
#    },
#    'VIF_metrics': {
#        'options': [None, 'Virtual InterFaces', 'kiB/s', 'bandwidth', 'pif.metrics'],
#        'lines': [
#            ['io_read_kbs', 'Read bandwidth'],
#            ['io_write_kbs', 'Write bandwidth'],
#        ],
#    },
#    # http://docs.vmd.citrix.com/XenServer/6.5.0/1.0/en_gb/api/?c=VM_guest_metrics
#    'VM_guest_metrics': {
#        'options': [None, 'metrics reported by the guest', None, 'VM.guest', 'VM.guest.metrics', 'stacked'],
#        'lines': [
#            ['memory', 'free/used/total memory', None],
#        ],
#    },
#    'VM_metrics_CPU': {
#        'options': [None, "Guest VCPUs", 'number', 'VM', 'VM.metrics.CPU'],
#        'lines': [
#            ['VCPUs_number', "current number of VCPUs"],
#            ['VCPUs_utilisation', "utilisation for all of guest's current VCPUs"],
#        ],
#    },
#    'VM_metrics_mem': {
#        'options': [None, "Guest actual's memory", 'bytes', 'VM', 'VM.metrics'],
#        'lines': [
#            ['memory_actual', "guest actual\'s memory"],
#        ],
#    },
}





#dbg_file = open('/tmp/rdartigues.log', 'w', 1)
#dbg_file = __import__('sys').stdout
#dbg = lambda s:(dbg_file.write('%s\n'%(s,)), dbg_file.flush())

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
        self.__set_defaults()

        self.definitions = CHARTS
        self.order = sorted(CHARTS)

        if self.configuration.get('url'):
            self.url = self.configuration['url']
            match = _uri_credentials.match(self.url)
            if match:
                self.username = match.group('user')
                self.password = match.group('pass')
                self.url = self.url.replace(match.group('credentials'), '')


    def __set_defaults(self):
        '''set some defaults
        '''
        self.configuration.setdefault('dom0 on top', False)


    def check(self):
        """
        Check if service is able to connect to server
        :return: boolean
        """
        result = False
        try:
            result = self._connect()
        except:
            logger.error('check failed', exc_info=True)
        finally:
            logger.debug('check: %s', result, exc_info=True)
            return result


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
            logger.debug('missing module XenAPI, cannot connect')
            return False

        if not isinstance(self.session, XenAPI.Session) or force:
            if self.url and (self.username or self.password):
                self.session = XenAPI.Session(self.url)
            else:
                self.session = XenAPI.xapi_local()

            try:
                self.session.login_with_password(
                    self.username or '',
                    self.password or '',
                    '1.0',
                    'netdata',
                )
            except IOError:
                logger.error('unable to connect to: %s (check permissions on your socket)', self.session)
                # will work with:
                # chgrp netdata /var/xapi/xapi
                # chmod g+rw /var/xapi/xapi
                return False
            except:
                # TODO: if host is not master, connect to master
                logger.error('unable to connect to: %s', self.session, exc_info=True)
                return False

            host_ref = self.session.xenapi.session.get_this_host(self.session._session)
            host = self.session.xenapi.host.get_record(host_ref)
            logger.info(
                'connected to XenServer %s API version %s',
                host['hostname'],
                self.session._get_api_version(),
            )

        return isinstance(self.session, XenAPI.Session)


    def __get_VMs(self, host_ref):
        '''
        :rtype: dict
        '''
        data = {}
        mem_lines = {}
        cpu_lines = {}

        VMs = self.session.xenapi.VM.get_all_records_where(
            'field "resident_on" = "%s"' % (
                host_ref,
            )
        )

        for VM in VMs.itervalues():
            key = (VM['is_control_domain'], VM['uuid'])
            VM['metrics'] = self.session.xenapi.VM_metrics.get_record(VM['metrics'])

            # compute VM memory usage
            mem_key = 'VM.metrics.%(uuid)s.mem' % VM
            data[mem_key] = int(VM['metrics']['memory_actual'])
            mem_lines[key] = (mem_key, VM['uuid'], 'absolute', 1, _B2MiB)

            # compute VM CPU count
            cpu_key = 'VM.metrics.%(uuid)s.CPU.count' % VM
            data[cpu_key] = int(VM['metrics']['VCPUs_number'])
            cpu_lines[key] = (cpu_key, VM['uuid'], 'absolute')

        self.definitions['VMs.mem']['lines'] = [
            mem_lines[k]
            for k in sorted(mem_lines, reverse=self.configuration['dom0 on top'])
        ]

        self.definitions['VMs.cpu']['lines'] = [
            cpu_lines[k]
            for k in sorted(cpu_lines, reverse=self.configuration['dom0 on top'])
        ]

        return data


    def _get_data(self):
        """
        Get some data
        :rtype: dict or None
        """
        logger.debug('get_data: start')
        if not self._connect():
            logger.debug('get_data: aborted')
            return
        data = {}

        host_ref = self.session.xenapi.session.get_this_host(self.session._session)
        host = self.session.xenapi.host.get_record(host_ref)

        host['metrics'] = self.session.xenapi.host_metrics.get_record(host['metrics'])
        data['host.metrics.memory_free'] = int(host['metrics']['memory_free'])
        data['host.metrics.memory_used'] = int(host['metrics']['memory_total']) - int(host['metrics']['memory_free'])
        data['host.metrics.memory_total'] = int(host['metrics']['memory_total'])

        data.update(self.__get_VMs(host_ref))

        # self.session.xenapi.SR.get_all_records()

#        VMs = self.session.xenapi.VM.get_all_records()



#            if not VM['is_control_domain']:
#                VM['VDIs'] = (
#                    # ???
#                    self.get_domU_VDIs_from_name(VM['name_label'])
#                    or
#                    self.get_domU_VDIs_from_conf(VM['name_label'])
#                )

        logger.debug('get_data: data=%r', data)
        return data






logger.debug('loaded')

#if __name__ == '__main__':
#    logging.basicConfig(
#        format='%(levelname)s: %(message)s',
#        datefmt='%F %T',
#        level=logging.DEBUG,
#    )
#    self = Service({'update_every':3, 'priority':99999, 'retries':3})
#    self.check()
