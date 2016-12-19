#!/usr/bin/env python
# vim:set fileencoding=utf8 ts=4 sw=4 et:
'''
Resources:

* https://developer.nvidia.com/nvidia-system-management-interface

Sample configuration:

.. code-block:: yaml

   ---
   remote1:
     url: https://user:pass@example.net/
'''


'''
input samples::

    084:~$ nvidia-smi --format=csv,noheader,nounits --query-gpu=index,utilization.gpu,utilization.memory,memory.total,memory.used,memory.free,fan.speed,temperature.gpu                                   
    0, 0, 0, 4095, 10, 4085, 42, 33
    1, [Not Supported], [Not Supported], 1023, 722, 301, 30, 37

    143:~$ nvidia-smi --format=csv,noheader,nounits --query-gpu=index,utilization.gpu,utilization.memory,memory.total,memory.used,memory.free,fan.speed,temperature.gpu                                   
    0, 0, 0, 4095, 24, 4071, 42, 35
    1, 0, 12, 2047, 190, 1857, 25, 36

'''


# stdlib
import logging
import subprocess

# netdata dependency
from base import SimpleService




logging.basicConfig(
    filename='/tmp/rdartigues.log',
    format='%(asctime)s %(filename)s:%(lineno)d [%(levelname)s] %(funcName)s %(message)s',
    datefmt='%FT%T',
    level=logging.DEBUG,
)
logger = logging.getLogger('netdata.nvidia.smi')
logger.debug('module loaded')

#priority = 90000
retries = 3
update_every = 5

_shift1 = 1024
_shift2 = 1024*1024
_shift3 = 1024*1024*1024


#ORDER = [
#    'PIF_metrics',
#    'VBD_metrics',
#    'VIF_metrics',
#    'VM_guest_metrics',
#    'VM_metrics',
#]
METRICS = [
    'index',
    'utilization.gpu',
    'utilization.memory',
    'memory.total',
    'memory.used',
    'memory.free',
    'fan.speed',
    'temperature.gpu',
]

CHARTS = {
    # utilization.gpu [%], utilization.memory [%], memory.total [MiB], memory.used [MiB], memory.free [MiB], fan.speed [%], temperature.gpu
    'GPU': {
        'options': [None, 'GPU usage', '%', 'utilization', 'nvidia.utilization.gpu', 'stacked'],
        'lines': [
#            [None, None, 'used', 'absolute'],
            ['utilization.gpu.0', 'a', 'used', 'absolute'],
            ['utilization.gpu.1', None, 'used', 'absolute'],
        ],
    },
#    'memory': {
#        'options': [None, 'memory usage', '%', 'utilization', 'nvidia.utilization.memory', 'stacked'],
#        'lines': [
##            [None, None, 'used', 'absolute'],
#            [None, 'memory.total.0', 'used', 'absolute'],
#            [None, 'memory.total.1', 'used', 'absolute'],
#        ],
#    },
#    'temperature': {
#        'options': [None, 'GPU temperature', 'Celcius', 'temperature', 'nvidia.temperature.gpu', 'line'],
#        'lines': [
#            [None, None, 'absolute', 1, 1000],
#        ],
#    },
#    'host': {
#        'options': [None, "Host memory usage", "GiB", 'mem', 'host.metrics', 'stacked'],
#        'lines': [
#            ['host.metrics.memory_free', 'free', 'absolute', 1, _shift2],
#            ['host.metrics.memory_used', 'used', 'absolute', 1, _shift2],
#        ],
#    },
#    'VMs.cpu.count': {
#        'options': [None, 'VM vCPU count', 'count', 'CPU', 'vm.metrics', 'line'],
#        'lines': [
#            # set by Service.__get_VMs
#        ],
#    },
#    'VMs.cpu.usage': {
#        'options': [None, 'VM CPU usage, 100 % means one vCPU', 'CPU %', 'CPU', 'vm.metrics', 'stacked'],
#        'lines': [
#            # set by Service.__get_VMs
#        ],
#    },
#    'VBD.io': {
#        'options': [None, 'I/O from VM', 'MiB/s', 'VM I/O', 'vm.metrics'],
#        'lines': [
#            # set by Service.__get_VMs
#        ],
#    },
#    'VBD.iops': {
#        'options': [None, 'I/O requests/s from VM', 'IO/s', 'VM I/O', 'vm.metrics'],
#        'lines': [
#            # set by Service.__get_VMs
#        ],
#    },
##    'PIF_metrics': {
##        'options': [None, 'Physical InterFaces', 'kiB/s', 'bandwidth', 'pif.metrics'],
##        'lines': [
##            ['io_read_kbs', 'Read bandwidth'],
##            ['io_write_kbs', 'Write bandwidth'],
##        ],
##    },
##    'VBD_metrics': {
##        'options': [None, 'Virtual Block Device', 'kiB/s', 'bandwidth', 'vbd.metrics'],
##        'lines': [
##            ['io_read_kbs', 'Read bandwidth'],
##            ['io_write_kbs', 'Write bandwidth'],
##        ],
##    },
#    'VIF_metrics': {
#        'options': [None, 'Virtual InterFaces', 'kiB/s', 'bandwidth', 'vif.metrics'],
#        'lines': [
#            # set by Service.__get_VMs
##            ['io_read_kbs', 'Read bandwidth'],
##            ['io_write_kbs', 'Write bandwidth'],
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
    __command = None
    __headers_set = False

    def __init__(self, configuration=None, name=None):
        logger.debug('called: %r', locals())
        SimpleService.__init__(self, configuration, name)
        self.command = 'nvidia-smi'
        self.definitions = CHARTS
        self.order = sorted(CHARTS)
        self.configuration.setdefault(
            'query gpu',
            [
                'utilization.gpu',
                'utilization.memory',
                'memory.total',
                'memory.used',
                'memory.free',
                'fan.speed',
                'temperature.gpu',
            ]
        )


    def _command(self):
        if not self.__command:
            # ensure "index" is in the list
            index = 'index'
            if index not in self.configuration['query gpu']:
                self.configuration['query gpu'] += [index]
            query_gpu = ','.join(self.configuration['query gpu'])

            self.configuration['query gpu']
            self.__command = (
                self.command,
                '--format=csv,noheader,nounits',
                '--query-gpu=%s' % (
                    query_gpu,
                ),
            )

        return self.__command


    def _get_raw_data(self):
        '''
        :return: status connection
        :rtype: bool
        '''
        try:
            p = subprocess.Popen(
                self._command(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except Exception as e:
            self.error("Executing command", ' '.join(self._command()), "resulted in error:", str(e))
            return None

        data = [
            str(line.decode())
            for line in p.stdout.readlines()
        ]

        if not data:
            self.error("No data collected.")
            return None

        return data


#    def _process_data(self, data):
#        logger.debug('called')
#        data = []
#        for line in self._get_raw_data():
#            row = {}
#            for k, v in zip(self.configuration['query gpu'], line.split(',')):
#                row[k] = cast(v.split(None, 1)[0], -1, int)
#            data+= [row]
#        logger.debug('get data return: %r', data)
#        return data


    def _get_data(self):
        '''
        '''
#        for k, v in self.definitions.items():
#            options = v['options']
#            lines = v['lines']
#            line = lines[0] if lines else None
#            if len(lines) == 1 and line[0] == line[1] == None:
#                self.definitions[k]['lines'] = [
#                    [
#                        '%s.%s' % (
#                            options[4].lstrip('nvidia.'),
#                            row['index'],
#                        )
#                    ] + line[2:]
#                    for row in data
#                ]
        logger.debug('called')
        import random
        return {
            'utilization.gpu.0': random.randint(0, 100),
            'utilization.gpu.1': random.randint(0, 100),
            'temperature.gpu.0': random.randint(0, 100),
            'temperature.gpu.1': random.randint(0, 100),
        }
        data = {}
        for line in self._get_raw_data():
            row = {
                k: cast(v.split(None, 1)[0], -1, int)
                for k, v in zip(self.configuration['query gpu'], line.split(','))
            }
            index = row.pop('index')
            for k, v in row.items():
                data[ '%s.%s' % (k, index) ] = v
        logger.debug('get data return: %r', data)
        return data


    def __create_definitions(self):
        logger.debug('called')
        data = self._get_data()
        for k, v in self.definitions.items():
            options = v['options']
            lines = v['lines']
            line = lines[0] if lines else None
            if len(lines) == 1 and line[0] == line[1] == None:
                self.definitions[k]['lines'] = [
                    [
                        '%s.%s' % (
                            options[4].lstrip('nvidia.'),
                            row['index'],
                        )
                    ] + line[2:]
                    for row in data
                ]


    def check(self):
#        self.__create_definitions()
        return SimpleService.check(self)






logger.debug('loaded')


def cast(value, default=None, to=str, *args, **kwargs):
    '''cast a value to a type or return default

    :param mixed value: value to cast
    :param mixed default: default value to return
    :param type to: cast method
    :param list args: passed to the casting method
    :param dict kwargs: passed to the casting method

    Example::

       >>> map(lambda v:cast(v, -1, int), [' 1', '[Not Available]', '20'])
       [1, -1, 20]
       >>> map(cast, [3, u'\u9898', 'foobar'])
       ['3', None, 'foobar']
    '''
    try:
        return to(value, *args, **kwargs)
    except:
        return default


#if False: # if True:
#    import user;from pprint import pprint;user;pprint
#    self = Service({'update_every':3, 'priority':99999, 'retries':3})
#    host_ref = self.session.xenapi.session.get_this_host(self.session._session)
#
#
#    Self = Service({'update_every':3, 'priority':99999, 'retries':3, 'url': 'https://root:sdfsdf@localhost'})
#if __name__ == '__main__':
#    logging.basicConfig(
#        format='%(levelname)s: %(message)s',
#        datefmt='%F %T',
#        level=logging.DEBUG,
#    )
#    self.check()
