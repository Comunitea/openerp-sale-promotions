# -*- coding: utf-8 -*-
# © 2016 Comunitea - Javier Colmenero <javier@comunitea.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp.osv import orm, fields


class ResPartner(orm.Model):

    _inherit = 'res.partner'

    _columns = {
        'rule_ids': fields.many2many('promos.rules',
                                     'rule_partner_rel',
                                     'rule_id',
                                     'partner_id',
                                     string="Comercial Rules",
                                     help="Comercial rules belongs to this \
                                           customer"),
    }
