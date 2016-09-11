#!/usr/bin/env python
# vim:set fileencoding=utf8 ts=4 sw=4 et:

# netdata dependency
from base import SimpleService

# Xen API Python modle
try:
    import XenAPI
except ImportError:
    XenAPI = None

# See: https://github.com/firehol/netdata/wiki/How-to-write-new-module
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
