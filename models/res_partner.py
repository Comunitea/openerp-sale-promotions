# -*- coding: utf-8 -*-
# © 2016 Comunitea - Javier Colmenero <javier@comunitea.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp.osv import orm, fields
from openerp import api
import time


class ResPartner(orm.Model):

    _inherit = 'res.partner'

    def _rules_count(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for partner in self.browse(cr, uid, ids, context=context):
            res[partner.id] = len(partner._get_customer_related_promos())
        return res

    _columns = {
        'rule_ids': fields.many2many('promos.rules',
                                     'rule_partner_rel',
                                     'rule_id',
                                     'partner_id',
                                     string="Comercial Rules",
                                     help="Comercial rules belongs to this \
                                           customer"),
        'rules_count': fields.function(_rules_count, string='# Customer Rules',
                                       type='integer'),
    }

    @api.multi
    def action_show_expense(self):
        res = {}
        t_promo = self.env['promos.rules']

        line_ids = t_promo.get_expense_lines([])
        res = {
            'domain': str([('id', 'in', line_ids)]),
            'view_type': 'tree',
            'view_mode': 'tree',
            'res_model': 'promos.rules',
            'type': 'ir.actions.act_window',
            'nodestroy': True
        }
        return res

    @api.multi
    def _get_customer_related_promos(self):
        t_promo = self.env['promos.rules']
        today = time.strftime("%Y-%m-%d")
        categ_ids = []
        if self.category_id:
            categ_ids = [x.id for x in self.category_id]
        domain = ['&', '&', '&', '&',
                  ('active', '=', True),
                  '|',
                  ('partner_ids', '=', False),
                  ('partner_ids', 'in', [self.id]),
                  '|',
                  ('partner_categories', '=', False),
                  ('partner_categories', 'in', categ_ids),
                  '|',
                  ('from_date', '=', False),
                  ('from_date', '>=', today),
                  '|',
                  ('to_date', '=', False),
                  ('to_date', '<=', today)]
        promo_objs = t_promo.search(domain)
        return promo_objs

    @api.multi
    def buttom_view_promotions(self):
        self.ensure_one()
        promo_objs = self._get_promos_domain()
        res = {
            'domain': str([('id', 'in', [x.id for x in promo_objs])]),
            # 'view_type': 'tree',
            'view_mode': 'tree,form',
            'res_model': 'promos.rules',
            'type': 'ir.actions.act_window',
            'nodestroy': True
        }
        return res
