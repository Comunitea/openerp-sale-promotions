# -*- coding: utf-8 -*-
# © Openlabs Technologies & Consulting (P) Limited
# © 2016 Comunitea - Javier Colmenero <javier@comunitea.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

{
    'name': 'Comercial Rules and Promotios',
    'version': '8.0.0.0',
    'author': 'Openlabs Technologies & Consulting (P) Limited, ',
              'Comunitea'
    'website': 'http://openlabs.co.in',
    'category': 'Generic Modules/Sales & Purchases',
    'depends': ['base', 'sale'],
    'data': [
        'data/product_data.xml',
        'views/rule.xml',
        'views/sale.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
