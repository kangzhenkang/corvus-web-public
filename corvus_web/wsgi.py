# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .app import create_api_app, create_web_app

app = create_api_app()
webapp = create_web_app()
