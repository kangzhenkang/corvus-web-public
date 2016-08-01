# -*- coding: utf-8 -*-

from __future__ import absolute_import

from logging.config import dictConfig

__version__ = '0.4.3'

dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'corvus': {
            'handlers': ['console'],
            'propagate': False,
            'level': 'INFO',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'console'
        },
    },
    'formatters': {
        'console': {
            'format': '%(asctime)s [%(levelname)s] [%(name)s][%(process)d]'
            ': %(message)s',
        },
    }
})
