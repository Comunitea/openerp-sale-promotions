# -*- coding: utf-8 -*-
# © 2016 Comunitea - Javier Colmenero <javier@comunitea.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


from openerp import models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # def _create_invoice_line_from_vals(self, cr, uid, move, invoice_line_vals, context=None):
    #     sl_obj = self.pool.get('sale.order.line')
    #     il_obj = self.pool.get('account.invoice.line')
    #     import ipdb; ipdb.set_trace()
    #     if context.get('inv_type') in ('out_invoice') and move.procurement_id \
    #             and move.procurement_id.sale_line_id:

    #         sale_line = move.procurement_id.sale_line_id
    #         domain = [
    #             ('order_id', '=', move.procurement_id.sale_line_id.order_id.id),
    #             ('promotion_line', '=', True)
    #         ]
    #         sale_lines = sl_obj.search(cr, uid, domain, context=context)
    #         for promo_line in sl_obj.browse(cr, uid, sale_lines, context):
    #             for l in promo_line.orig_line_ids:
    #                 if l.id == sale_line.id:
    #                     new_line_vals = invoice_line_vals.copy()
    #                     new_line_vals.update({
    #                         'name': promo_line.name,
    #                         'product_id': promo_line.product_id.id,
    #                         'quantity': move.product_uom_qty,
    #                         'uos_id': promo_line.product_uom.id,
    #                     })
    #                     il_obj.create(cr, uid, new_line_vals, context)
    #                     promo_line.write({'invoiced': True})

    #     invoice_line_id = super(stock_move, self)._create_invoice_line_from_vals(cr, uid, move, invoice_line_vals, context=context)
    #     import ipdb; ipdb.set_trace()
    #     return invoice_line_id

    @api.multi
    def action_invoice_create(self, journal_id, group=False, type='out_invoice'):
        """ Creates invoice based on the invoice state selected for picking.
        @param journal_id: Id of journal
        @param group: Whether to create a group invoice or not
        @param type: Type invoice to be created
        @return: Ids of created invoices for the pickings
        """
        res = super(StockPicking, self).action_invoice_create(journal_id, group=group, type=type,)
        for inv in self.env['account.invoice'].browse(res):
            # import ipdb; ipdb.set_trace()
            for l in inv.invoice_line:
                domain = [('invoice_lines', 'in', [l.id])]
                sale_line = self.env['sale.order.line'].search(domain)
                if sale_line:
                    domain = [
                        ('order_id', '=', sale_line.order_id.id),
                        ('promotion_line', '=', True),
                        ('orig_line_ids', 'in', [sale_line.id])
                    ]
                    promo_lines = self.env['sale.order.line'].search(domain)
        return res
