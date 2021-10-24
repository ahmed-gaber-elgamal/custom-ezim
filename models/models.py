# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ConfigurationEzim(models.Model):
    _name = 'network.providers'
    _rec_name = 'provider_name'

    provider_name = fields.Char(string="Network Provider", required=True)
