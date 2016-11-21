"""
Adding voucher codes for sale order

This design is inspired by magento
"""
#########################################################################
#                                                                       #
# Copyright (C) 2010-2013 Openlabs Technologies & Consulting (P) Limited#
# Special Credit: Yannick Buron for design evaluation                   #
#                                                                       #
#This program is free software: you can redistribute it and/or modify   #
#it under the terms of the GNU General Public License as published by   #
#the Free Software Foundation, either version 3 of the License, or      #
#(at your option) any later version.                                    #
#                                                                       #
#This program is distributed in the hope that it will be useful,        #
#but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
#GNU General Public License for more details.                           #
#                                                                       #
#You should have received a copy of the GNU General Public License      #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.  #
#########################################################################
from openerp.osv import orm, fields

class SaleOrder(orm.Model):
    '''
    Sale Order
    '''
    _inherit = 'sale.order'

    _columns = {
        'coupon_code':fields.char('Promo Coupon Code', size=20),
    }

    def clear_existing_promotion_lines(self, cursor, user,
                                        order_id, context=None):
        """
        Deletes existing promotion lines before applying
        @param cursor: Database Cursor
        @param user: ID of User
        @param order: Sale order id
        @param context: Context(no direct use).
        """
        order = self.browse(cursor, user, order_id, context)
        order_line_obj = self.pool.get('sale.order.line')
        #Delete all promotion lines
        order_line_ids = order_line_obj.search(cursor, user,
                                            [
                                             ('order_id', '=', order.id),
                                             ('promotion_line', '=', True),
                                            ], context=context
                                            )
        if order_line_ids:
            order_line_obj.unlink(cursor, user, order_line_ids, context)
        #Clear discount column
        order_line_ids = order_line_obj.search(cursor, user,
                                            [
                                             ('order_id', '=', order.id),
                                            ], context=context
                                            )
        for line in order_line_obj.browse(cursor, user, order_line_ids, context):
            if line.orig_qty:
                order_line_obj.write(cursor, user, [line.id], {'product_uom_qty': line.orig_qty}, context)
            if line.old_discount:
                order_line_obj.write(cursor, user,
                                     order_line_ids,
                                     {'discount': line.old_discount,
                                      'old_discount': 0.00},
                                     context=context)
        return True

    def apply_promotions(self, cursor, user, ids, context=None):
        """
        Applies the promotions to the given records
        @param cursor: Database Cursor
        @param user: ID of User
        @param ids: ID of current record.
        @param context: Context(no direct use).
        """
        promotions_obj = self.pool.get('promos.rules')
        for order_id in ids:
            self.clear_existing_promotion_lines(cursor, user, order_id, context)
            promotions_obj.apply_promotions(cursor, user,
                                            order_id, context=None)

        return True


class SaleOrderLine(orm.Model):
    '''
    Sale Order Line
    '''
    _inherit = "sale.order.line"

    _columns = {
        'promotion_line':fields.boolean(
                "Promotion Line",
                help="Indicates if the line was created by promotions"
                ),
        'orig_qty': fields.float('Original qty'),
        'old_discount': fields.float('Old discount', digits=(5,2),
                                     readonly=True)

    }
