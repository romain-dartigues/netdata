#!/usr/bin/env python
# vim:set fileencoding=utf8 ts=4 sw=4 et:
'''
Resources:

* https://github.com/firehol/netdata/wiki/How-to-write-new-module
* https://github.com/firehol/netdata/wiki/External-Plugins
* http://docs.citrix.com/content/dam/docs/en-us/xenserver/xenserver-7-0/downloads/xenserver-7-0-management-api-guide.pdf

Sample configuration:

.. code-block:: yaml

   ---
   remote1:
     url: https://user:pass@example.net/
'''

# stdlib
import collections
import logging
import re
import sys
import time
import urllib
import xml.dom.minidom

logging.basicConfig(
    filename='/opt/netdata/var/log/netdata/xenserver.log',
    format='%(asctime)s %(filename)s:%(lineno)d [%(levelname)s] %(message)s',
    datefmt='%FT%T',
    level=logging.DEBUG,
)
logger = logging.getLogger('netdata.xenserver')
logger.debug('module loaded')

# netdata dependency
try:
    from bases.FrameworkServices.SimpleService import SimpleService
except Exception as err:
    logger.fatal('unable to load netdata dependencies', exc_info=True)
    raise


# Xen API Python modle
try:
    import XenAPI
except ImportError:
    XenAPI = None




#priority = 90000
retries = 10
update_every = 5

_shift1 = 1024
_shift2 = 1024*1024
_shift3 = 1024*1024*1024

_uri = re.compile(r'''
^
(?:
    (?P<scheme>[^:]*?)
    ://
        (?P<credentials>
        (?P<username>[^:]*?)
        :
        (?P<password>[^@]*]?)
        @
    )?
)?
(?P<netloc>
    (?P<hostname>[^/:]+?)
    (?:
        \:
        (?P<port>\d+?)
    )?
)?
(?:
    (?P<path>/[^#]*?)
    (?P<fragment>\#.*)?
)?
$
''', re.X | re.I)


#ORDER = [
#    'PIF_metrics',
#    'VBD_metrics',
#    'VIF_metrics',
#    'VM_guest_metrics',
#    'VM_metrics',
#]

CHARTS = {
    'host': {
        'options': [None, "Host memory usage", "GiB", 'mem', 'host.metrics', 'stacked'],
        'lines': [
            ['host.metrics.memory_free', 'free', 'absolute', 1, _shift2],
            ['host.metrics.memory_used', 'used', 'absolute', 1, _shift2],
        ],
    },
    # 'VMs.mem': {
    #     'options': [None, "VM memory usage", "MiB", 'mem', 'vm.metrics', 'stacked'],
    #     'lines': [
    #         # set by Service.__get_VMs
    #     ],
    # },
    # 'VMs.cpu.count': {
    #     'options': [None, 'VM vCPU count', 'count', 'CPU', 'vm.metrics', 'line'],
    #     'lines': [
    #         # set by Service.__get_VMs
    #     ],
    # },
    # 'VMs.cpu.usage': {
    #     'options': [None, 'VM CPU usage, 100 % means one vCPU', 'CPU %', 'CPU', 'vm.metrics', 'stacked'],
    #     'lines': [
    #         # set by Service.__get_VMs
    #     ],
    # },
    # 'VBD.io': {
    #     'options': [None, 'I/O from VM', 'MiB/s', 'VM I/O', 'vm.metrics'],
    #     'lines': [
    #         # set by Service.__get_VMs
    #     ],
    # },
    # 'VBD.iops': {
    #     'options': [None, 'I/O requests/s from VM', 'IO/s', 'VM I/O', 'vm.metrics'],
    #     'lines': [
    #         # set by Service.__get_VMs
    #     ],
    # },
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
#     'VIF_metrics': {
#         'options': [None, 'Virtual InterFaces', 'kiB/s', 'bandwidth', 'vif.metrics'],
#         'lines': [
#             # set by Service.__get_VMs
# #            ['io_read_kbs', 'Read bandwidth'],
# #            ['io_write_kbs', 'Write bandwidth'],
#         ],
#     },
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

class RRDUpdates(dict):
    '''map a rrd_updates to a nice dict

    Resources:

    * http://www.xenserver.org/partners/developing-products-for-xenserver/18-sdk-development/96-xs-dev-rrds.html

    ::

       {'machine_uuid': {'type': 'host', 'metric_name': 0.123, ...}, ... }

    .. Warning::
       The VM RRDs are stored on the host on which they run, or the pool master
       when they are not running.
    '''
    start = 0
    step = 60
    end = 0
    params = None


    def __init__(self, session, server='localhost', start=None, step=5, host=True):
        '''
        :param :class:`XenAPI.Session` session:
        :param str server:
        :param start: start timestamp (default: now)
        :type start: None or int
        :param int step: interval
        :param bool host: if True, include host RRD
        '''
        self.server = server
        self.params = {
            'session_id': session.handle,
            'start': start or time.time().__int__() - step,
            'host': 'true' if host else 'false',
            'cf': 'AVERAGE',
            'interval': step,
        }


    def refresh(self, **kwargs):
        '''refresh the data

        :param kwargs: update the request parameters
        '''
        self.params.update(kwargs)

        uri = 'http://%s/rrd_updates?%s' % (
            self.server,
            '&'.join('%s=%s' % r for r in self.params.iteritems()),
        )
        fileobj = urllib.URLopener().open(uri)

        meta, data = xml.dom.minidom.parse(fileobj).firstChild.childNodes

        self.start = int(meta.getElementsByTagName('start')[0].firstChild.data)
        self.step = int(meta.getElementsByTagName('step')[0].firstChild.data)
        self.end = int(meta.getElementsByTagName('end')[0].firstChild.data)

        # aggregate statistics
        avg = [0] * int(meta.getElementsByTagName('columns')[0].firstChild.data)
        for row in data.childNodes:
            # each row is a time entry
            for i, v in enumerate(row.getElementsByTagName('v')):
                # each "v" is a value
                avg[i] += float(v.firstChild.data)
        l = int(meta.getElementsByTagName('rows')[0].firstChild.data)
        if not l:
            # TODO: logging.debug('RRDUpdates.refresh() no data?...
            return
        avg = tuple(i / l for i in avg)

        # associate averages with their machine / metric name
        result = {}
        for i, row in enumerate(meta.getElementsByTagName('legend')[0].childNodes):
            t, uuid, name = row.firstChild.data.encode('latin1').split(':')[1:]
            if uuid not in result:
                result[uuid] = {'type': t}
            result[uuid][name] = avg[i]
        self.clear()
        self.update(result)

        self.params['start'] = self.end + 1


    def get_VM_simple(self, uuid):
        '''
        :param str uuid: vm uuid
        :rtype: collections.defaultdict
        '''
        RRD = self.get(uuid, {})
        # this should contains a dict with keys like:
        # cpu0, cpu1, ...
        # memory, memory_internal_free, memory_target
        # type (vm or host)
        # vbd_xvda_inflight, vbd_xvda_io_throughput_read, vbd_xvda_io_throughput_total, vbd_xvda_io_throughput_write, vbd_xvda_iops_read, vbd_xvda_iops_total, vbd_xvda_iops_write, vbd_xvda_iowait, vbd_xvda_read, vbd_xvda_read_latency, vbd_xvda_write, vbd_xvda_write_latency, ...
        metrics = collections.defaultdict(int)

        for k, v in RRD.iteritems():
            if k[:3] == 'cpu':
                metrics['cpu_count'] += 1
                key = k[:3]
            elif k[:4] == 'vbd_':
                key = k[:4] + k[4:].partition('_')[-1]
#            elif k.startswith('vif'): TODO
            elif k[:6] == 'memory':
                key = k
            else:
                continue
            metrics[key] += v

        return metrics


        def __missing__(self, key):
            return collections.defaultdict(int)



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

    server = 'localhost'
    '''host of the XenServer (for RRD)
    '''

    RRD = None

    def __init__(self, configuration=None, name=None):
        SimpleService.__init__(self, configuration, name)
        self.definitions = CHARTS
        self.order = sorted(CHARTS)
        self.configuration.setdefault('dom0 on top', False)
        self.configuration.setdefault('uuid for VM', False)

        if self.configuration.get('url'):
            self.url = self.configuration['url']
            match = _uri.match(self.url)
            if match:
                self.username = match.group('username')
                self.password = match.group('password')
                self.server = match.group('hostname')
                self.url = self.url.replace(match.group('credentials'), '')
        logger.debug('Service(configuration=%r, name=%r)', configuration, name)


    def check(self):
        """
        Check if service is able to connect to server
        :return: boolean
        """
        # return True
        result = False
        try:
            result = self._connect()
        except:
            logger.error('check failed', exc_info=True)
        finally:
            logger.debug('check: %s', result, exc_info=True)
            return result


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
                logger.info('connection to: %s (%s:%s)', self.url, self.username, self.password)
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
                logger.error('unable to connect to: %s (check permissions on your socket)', self.session, exc_info=True)
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
                self.session.API_version,
            )

            # setup RRDs
            self.RRD = RRDUpdates(
                self.session,
                self.server,
                step=self.update_every,
            )

        return isinstance(self.session, XenAPI.Session)


    def __get_VMs(self, host_ref):
        '''
        Compute data for VM and set some lines of :attr:`definitions`.

        :rtype: dict
        '''
        data = {}
        tree = collections.defaultdict(dict)
        name_key = 'uuid' if self.configuration['uuid for VM'] else 'name_label'
        dom0_on_top = self.configuration['dom0 on top']

        VMs = self.session.xenapi.VM.get_all_records_where(
            'field "resident_on" = "%s"' % (
                host_ref,
            )
        )

        for VM in VMs.itervalues():
            metrics = self.RRD.get_VM_simple(VM['uuid'])
            key = (VM['is_control_domain'], VM['uuid'])
            name = VM[name_key]

            # VM memory usage
            k = 'VM.metrics.%(uuid)s.mem' % VM
            data[k] = metrics['memory']
            tree['VMs.mem'][key] = (k, name, None, 1, _shift2)

            # VM CPU count
            k = 'VM.metrics.%(uuid)s.CPU.count' % VM
            data[k] = metrics['cpu_count']
            tree['VMs.cpu.count'][key] = (k, name)

            # VM CPU usage
            k = 'VM.metrics.%(uuid)s.CPU.usage' % VM
            data[k] = metrics['cpu'] * 100
            tree['VMs.cpu.usage'][key] = (k, name)

            # VIF_metrics
            # TODO

            # I/O
            k = 'VM.metrics.%(uuid)s.io.read' % VM
            data[k] = metrics['vbd_read']
            tree['VBD.io'][key + ('read',)] = (k, '%s read' % (name,), None, 1, _shift2)

            k = 'VM.metrics.%(uuid)s.io.write' % VM
            data[k] = metrics['vbd_write']
            tree['VBD.io'][key + ('write', )] = (k, '%s write' % (name,), None, -1, _shift2)

            # I/O/s
            k = 'VM.metrics.%(uuid)s.ips' % VM
            data[k] = metrics['vbd_iops_read'] * 1000
            tree['VBD.iops'][key + ('i',)] = (k, '%s read' % (name,), None, 1, 100)

            k = 'VM.metrics.%(uuid)s.ops' % VM
            data[k] = metrics['vbd_iops_write'] * 100
            tree['VBD.iops'][key + ('o', )] = (k, '%s write' % (name,), None, -1, 100)

        del k
        # sort all lines
        for key, item in tree.iteritems():
            self.definitions[key]['lines'] = [
                item[k]
                for k in sorted(item, reverse=dom0_on_top)
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
        self.RRD.refresh()

        host_ref = self.session.xenapi.session.get_this_host(self.session._session)
        host = self.session.xenapi.host.get_record(host_ref)

        host_metrics = self.RRD[host['uuid']]
        data['host.metrics.memory_free'] = host_metrics['memory_free_kib'] * _shift1
        data['host.metrics.memory_total'] = host_metrics['memory_total_kib'] * _shift1
        data['host.metrics.memory_used'] = data['host.metrics.memory_total'] - data['host.metrics.memory_free']

        data.update(self.__get_VMs(host_ref))

        # self.session.xenapi.SR.get_all_records()

#        VMs = self.session.xenapi.VM.get_all_records()

        logger.debug('get_data: data=%r', data)
        return data




def XenAPI_Session__init__(self, uri, transport=None, encoding=None, verbose=0, allow_none=1, ignore_ssl=False):
    if ignore_ssl:
        import ssl
        ctx = ssl._create_unverified_context()
        xmlrpclib.ServerProxy.__init__(self, uri, transport, encoding, verbose, allow_none, context=ctx)
    self.transport = transport
    self._session = None
    self.last_login_method = None
    self.last_login_params = None
    self.API_version = XenAPI.API_VERSION_1_1


#logger.debug('loaded')

r'''
session = XenAPI.xapi_local()
session.login_with_password('', '', '1.0', 'netdata')


session = XenAPI.Session('https://localhost')
session.login_with_password('root', 'sdfsdf06', '1.0', 'netdata')

'''

#if __name__ == '__main__' and 'test' in sys.argv:
#    import user;from pprint import pprint;user;pprint
#    self = Service({'update_every':3, 'priority':99999, 'retries':3})
#    host_ref = self.session.xenapi.session.get_this_host(self.session._session)
#
#
#    Self = Service({'update_every':3, 'priority':99999, 'retries':3, 'url': 'https://root:sdfsdf06@localhost'})
#    pprint(self.check())
#if __name__ == '__main__':
#    logging.basicConfig(
#        format='%(levelname)s: %(message)s',
#        datefmt='%F %T',
#        level=logging.DEBUG,
#    )
#    self.check()
#    /etc/xensource/xapi-ssl.pem
