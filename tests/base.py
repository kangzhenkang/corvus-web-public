# -*- coding: utf-8 -*-
import logging
import unittest2
import os
from corvus_web.app import create_app

logger = logging.getLogger(__name__)


class Base(unittest2.TestCase):
    def setUp(self):
        logger.info('----------set up----------')
        self.client = create_app().test_client()

    def tearDown(self):
        logger.info('----------tear down----------')
        os.remove('/tmp/coruvs-web.db')
