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
import collections
import logging
import subprocess

# netdata dependency
from base import SimpleService




logging.basicConfig(
    filename='/tmp/rdartigues.log',
    format='%(asctime)s %(filename)s:%(lineno)d [%(levelname)s] %(funcName)s() %(message)s',
    datefmt='%FT%T',
    level=logging.DEBUG,
)
logger = logging.getLogger('netdata.nvidia.smi')
logger.debug('module loaded')

#priority = 90000
retries = 3
update_every = 5


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
        'options': [None, 'GPU usage', '%', 'utilization', 'nvidia.utilization.gpu', 'line'],
        'lines': [ ],
        'template': ['utilization.gpu', 'GPU', 'absolute'],
    },
    'memory': {
        'options': [None, 'memory usage', '%', 'utilization', 'nvidia.utilization.memory', 'stacked'],
        'lines': [],
        'template': ['utilization.memory', 'GPU', 'absolute'],
    },
    'fan': {
        'options': [None, 'fan speed', '%', 'fan', 'nvidia.fan.speed', 'line'],
        'lines': [ ],
        'template': ['fan.speed', 'GPU', 'absolute'],
    },
    'temperature': {
        'options': [None, 'GPU temperature', 'Celcius', 'temperature', 'nvidia.temperature.gpu', 'line'],
        'lines': [ ],
        'template': ['temperature.gpu', 'GPU', 'absolute'],
    },
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
        logger.debug('called')
        data = {}
        categories = collections.defaultdict(list)
        for line in self._get_raw_data():
            row = {
                k: cast(v.split(None, 1)[0], -1, int)
                for k, v in zip(self.configuration['query gpu'], line.split(','))
            }
            index = row.pop('index')
            for k, v in row.items():
                key = '%s.%s' % (k, index)
                categories[k]+= [key]
                data[key] = v
        self.__create_definitions(categories, data)
        logger.debug('get data return: %r', data)
        return data


    def __create_definitions(self, categories, data):
        logger.debug('called')
        changed = False
        for k, v in self.definitions.items():
            if v['lines']:
                continue
            changed = True
            template = v['template']
            category = categories[template[0]]
            self.definitions[k]['lines'] = [
                [
                    identifier,
                    template[1] + ' ' + identifier.rpartition('.')[-1],
                ] + template[2:]
                for identifier in category
            ]
        if changed:
            logger.info('definitions changed: %r', self.definitions)


    def check(self):
        logger.debug('called')
#        self.__create_definitions()
        return SimpleService.check(self)

    def create(self):
        """
        Create charts
        :return: boolean
        """
        logger.debug('called')
        data = self._get_data()
        if data is None:
            self.debug("failed to receive data during create().")
            logger.debug('failed to receive data during create()')
            return False

        idx = 0
        try:
            for name in self.order:
                logger.debug('create: name=%s', name)
                options = self.definitions[name]['options'] + [self.priority + idx, self.update_every]
                self.chart(self.chart_name + "." + name, *options)
                # check if server has this datapoint
                for line in self.definitions[name]['lines']:
                    logger.debug('create: line=%s', line)
                    if line[0] in data:
                        self.dimension(*line)
                    else:
                        logger.debug('create: line not in data!')
                idx += 1
        except:
            logger.error('meh', exc_info=True)

        logger.info('data stream: %r', self._data_stream)
        self.commit()
        return True
#    def dimension(self, id, name=None, algorithm="absolute", multiplier=1, divisor=1, hidden=False):
#        ['utilization.gpu.0', 'a', 'used', 'absolute']


class ServiceTest(SimpleService):
    def __init__(self, configuration=None, name=None):
        super(self.__class__,self).__init__(configuration=configuration, name=name)

    def check(self):
        return True

    def create(self):
        self.chart("example.python_random", '', 'A random number', 'random number',
                   'random', 'random', 'line', self.priority, self.update_every)
        self.dimension('random1')
        self.commit()
        return True

    def update(self, interval):
        import random
        self.begin("example.python_random", interval)
        self.set("random1", random.randint(0, 100))
        self.end()
        self.commit()
        return True






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
