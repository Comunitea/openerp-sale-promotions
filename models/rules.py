# -*- coding: utf-8 -*-
# © 2016 Comunitea - Javier Colmenero <javier@comunitea.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from openerp.osv import orm, fields
from openerp.tools.misc import ustr
from openerp.tools.translate import _

DEBUG = True
PRODUCT_UOM_ID = 1

ATTRIBUTES = [
    ('amount_untaxed', _('Untaxed Total')),
    ('amount_tax', 'Tax Amount'),
    ('amount_total', 'Total Amount'),
    ('product', 'Product Code in order'),
    ('prod_qty', 'Product Quantity combination'),
    ('prod_unit_price', 'Product UnitPrice combination'),
    ('prod_sub_total', 'Product SubTotal combination'),
    # ('prod_net_price', 'Product NetPrice combination'),
    ('prod_discount', 'Product Discount combination'),
    ('prod_weight', 'Product Weight combination'),
    ('comp_sub_total', 'Compute sub total of products'),
    ('comp_sub_total_x', 'Compute sub total excluding products'),
    # ('tot_item_qty', 'Total Items Quantity'),
    # ('tot_weight', 'Total Weight'),
    # ('tot_item_qty', 'Total Items Quantity'),
    ('custom', 'Custom domain expression'),
    ('pallet', 'Number of entire pallets'),
    ('prod_pallet', 'Number pallets of product'),
    ('ship_address', 'Ship Address City'),
]

COMPARATORS = [
    ('==', _('equals')),
    ('!=', _('not equal to')),
    ('>', _('greater than')),
    ('>=', _('greater than or equal to')),
    ('<', _('less than')),
    ('<=', _('less than or equal to')),
    ('in', _('is in')),
    ('not in', _('is not in')),
]

ACTION_TYPES = [
    ('prod_disc_perc', _('Discount % on Product')),
    ('prod_disc_fix', _('Fixed amount on Product')),
    ('cart_disc_perc', _('Discount % on Sub Total')),
    ('cart_disc_fix', _('Fixed amount on Sub Total')),
    ('prod_x_get_y', _('Buy X get Y free')),
    ('line_prod_disc_perc', _('New line discount, over order subtotal')),
    ('line_discount_group_price', _('New line discount, over price unit')),
    ('line_discount_mult_pallet', _('New line discount, multiply of pallet')),
]


class PromotionsRules(orm.Model):
    "Promotion Rules"
    _name = "promos.rules"
    _description = __doc__
    _order = 'sequence'

    def count_coupon_use(self, cr, uid, ids,
                         name, arg, context=None):
        '''
        This function count the number of sale orders(not in cancelled state)
        that are linked to a particular coupon.
        '''
        sales_obj = self.pool.get('sale.order')
        res = {}
        for promotion_rule in self.browse(cr, uid, ids, context):
            if promotion_rule.coupon_code:
                # If there is uses per coupon defined check if its overused
                if promotion_rule.uses_per_coupon > -1:
                    domain = [
                        ('coupon_code', '=', promotion_rule.coupon_code),
                        ('state', '<>', 'cancel')
                    ]
                    matching_ids = sales_obj.search(cr, uid, domain,
                                                    context=context)
                res[promotion_rule.id] = len(matching_ids)
            else:
                res[promotion_rule.id] = 0
        return res

    _columns = {
        'name': fields.char('Promo Name', size=50, required=True),
        'description': fields.text('Description'),
        'active': fields.boolean('Active'),
        'stop_further': fields.boolean('Stop Checks',
                                       help="Stops further promotions being "
                                            "checked"),
        'partner_categories': fields.many2many('res.partner.category',
                                               'rule_partner_cat_rel',
                                               'category_id',
                                               'rule_id',
                                               copy=True,
                                               string="Partner Categories",
                                               help="Applicable to all if \
                                                     none is selected"),
        'coupon_code': fields.char('Coupon Code', size=20, required=False),
        'uses_per_coupon': fields.integer('Uses per Coupon'),
        'uses_per_partner': fields.integer('Uses per Partner'),
        'coupon_used': fields.function(count_coupon_use, method=True,
                                       type='integer',
                                       string='Number of Coupon Uses',
                                       help='The number of times this coupon \
                                             has been used.'),
        'from_date': fields.datetime('From Date'),
        'to_date': fields.datetime('To Date'),
        'sequence': fields.integer('Sequence', required=True),
        'logic': fields.selection([('and', 'All'), ('or', 'Any')],
                                  string="Logic",
                                  required=True),
        'expected_logic_result': fields.selection([('True', 'True'),
                                                   ('False', 'False')],
                                                  string="Output",
                                                  required=True),
        'expressions': fields.one2many('promos.rules.conditions.exps',
                                       'promotion',
                                       copy=True,
                                       string='Expressions/Conditions'),
        'actions': fields.one2many('promos.rules.actions', 'promotion',
                                   string="Actions",
                                   copy=True),
        'partner_ids': fields.many2many('res.partner',
                                        'rule_partner_rel',
                                        'partner_id',
                                        'rule_id',
                                        domain=[('customer', '=', True)],
                                        string="Partner",
                                        help="Applicable to all if \
                                              none is selected"),
    }
    _defaults = {
        'logic': lambda * a: 'and',
        'expected_logic_result': lambda * a: 'True',
        'active': lambda * a: 'True',
    }

    def promotion_date(self, str_date):
        """ Converts string date to date """
        import time
        try:
            return time.strptime(str_date, '%Y-%m-%d %H:%M:%S')
        except:
            try:
                return time.strptime(str_date, '%Y-%m-%d')
            except:
                return str_date

    def check_primary_conditions(self, cr, uid,
                                 promotion_rule, order, context):
        """
        Checks the conditions for
            Coupon Code
            Validity Date
        """
        sales_obj = self.pool.get('sale.order')
        # Check if the customer is in the specified partner cats
        if promotion_rule.partner_categories:
            applicable_ids = [
                category.id for category in promotion_rule.partner_categories
            ]
            partner_categories = [
                category.id for category in order.partner_id.category_id]
            if not set(applicable_ids).intersection(partner_categories):
                raise Exception("Not applicable to Partner Category")
        if promotion_rule.coupon_code:
            # If the codes don't match then this is not the promo
            if not order.coupon_code == promotion_rule.coupon_code:
                raise Exception("Coupon codes do not match")
            # Calling count_coupon_use to check whether no. of
            # uses is greater than allowed uses.
            count = self.count_coupon_use(cr, uid, [promotion_rule.id],
                                          True, None, context).values()[0]
            if count > promotion_rule.uses_per_coupon:
                raise Exception("Coupon is overused")
            # If a limitation exists on the usage per partner
            if promotion_rule.uses_per_partner > -1:
                domain = [
                    ('partner_id', '=', order.partner_id.id),
                    ('coupon_code', '=', promotion_rule.coupon_code),
                    ('state', '<>', 'cancel')
                ]
                matching_ids = sales_obj.search(cr, uid, domain,
                                                context=context)
                if len(matching_ids) > promotion_rule.uses_per_partner:
                    raise Exception("Customer already used coupon")

        # If a start date has been specified
        if promotion_rule.from_date and \
            not (self.promotion_date(
                order.date_order) >=
                self.promotion_date(promotion_rule.from_date)):
            raise Exception("Order before start of promotion")

        # If an end date has been specified
        if promotion_rule.to_date and \
            not (self.promotion_date(
                order.date_order) <=
                self.promotion_date(promotion_rule.to_date)):
            raise Exception("Order after end of promotion")

        # All tests have succeeded
        return True

    def evaluate(self, cr, uid, promotion_rule, order, context=None):
        """
        """
        if not context:
            context = {}
        expression_obj = self.pool.get('promos.rules.conditions.exps')
        try:
            self.check_primary_conditions(cr, uid, promotion_rule, order,
                                          context)
        except Exception, e:
            raise orm.except_orm("Check conditions", e)
        # Now to the rules checking
        expected_result = eval(promotion_rule.expected_logic_result)
        logic = promotion_rule.logic
        # Evaluate each expression
        for expression in promotion_rule.expressions:
            result = 'Execution Failed'
            try:
                result = expression_obj.evaluate(cr, uid, expression, order,
                                                 context)

                # For and logic, any False is completely false
                if (not (result == expected_result)) and (logic == 'and'):
                    return False
                # For OR logic any True is completely True
                if (result == expected_result) and (logic == 'or'):
                    return True
                # If stop_further is given, then execution stops  if the
                # condition was satisfied
                if (result == expected_result) and expression.stop_further:
                    return True
            except Exception, e:
                raise orm.except_orm("Expression Error", e)

        if logic == 'and':
            # If control comes here for and logic, then all conditions were
            # satisfied
            return True
        else:
            # if control comes here for OR logic, none were satisfied
            return False

    def execute_actions(self, cr, uid, promotion_rule, order_id, context):
        """
        """
        action_obj = self.pool.get('promos.rules.actions')

        order = self.pool.get('sale.order').browse(cr, uid,
                                                   order_id, context)
        for action in promotion_rule.actions:
            try:
                action_obj.execute(cr, uid, action.id,
                                   order, context=None)
            except Exception, error:
                raise error
        return True

    def _get_promotions_domain(self, order, partner=False, date_order=False):
        """
        Obtengo domain del tipo A AND (B OR C) AND (D OR F) ....
        """
        if not partner:
            partner = order.partner_id
        if not date_order:
            date_order = order.date_order
        categ_ids = []
        if partner.category_id:
            categ_ids = [x.id for x in partner.category_id]
        domain = ['&', '&', '&', '&',
                  ('active', '=', True),
                  '|',
                  ('partner_ids', '=', False),
                  ('partner_ids', 'in', [partner.id]),
                  '|',
                  ('partner_categories', '=', False),
                  ('partner_categories', 'in', categ_ids),
                  '|',
                  ('from_date', '=', False),
                  ('from_date', '>=', date_order),
                  '|',
                  ('to_date', '=', False),
                  ('to_date', '<=', date_order)]

        if categ_ids:
            domain += ['|', ('partner_categories', 'in', categ_ids),
                       ('partner_categories', '=', False)]
        else:
            domain += [('partner_categories', '=', False)]
        return domain

    def apply_promotions(self, cr, uid, order_id, context=None):
        """
        Get all active promiotions, evaluate it, and execute if evaluation
        is true
        """
        order = self.pool.get('sale.order').browse(cr, uid,
                                                   order_id, context=context)
        domain = self._get_promotions_domain(order)
        active_promos = self.search(cr, uid, domain, context=context)

        for promotion_rule in self.browse(cr, uid, active_promos, context):
            # Check partner restrict
            # if promotion_rule.partner_ids and \
            #         order.partner_id not in promotion_rule.partner_ids:
            #     continue

            result = self.evaluate(cr, uid, promotion_rule, order, context)
            if result:
                try:
                    self.execute_actions(cr, uid, promotion_rule, order_id,
                                         context)
                except Exception, e:
                    raise orm.except_orm("Promotions", ustr(e))

                # If stop further is true stop here
                if promotion_rule.stop_further:
                    return True
        return True


class PromotionsRulesConditionsExprs(orm.Model):
    "Expressions for conditions"
    _name = 'promos.rules.conditions.exps'
    _description = __doc__
    _order = "sequence"
    _rec_name = 'serialised_expr'

    def on_change(self, cr, uid, ids=None,
                  attribute=None, value=None, context=None):
        """
        Set the value field to the format if nothing is there
        """
        # If attribute is not there then return.
        # Will this case be there?
        if not attribute:
            return {}
        # If value is not null or one of the defaults
        if value not in [
            False,
            "'product_code'",
            "'product_code',0.00",
            "['product_code','product_code2']|0.00",
            "0.00",
        ]:
            return {}
        # Case 1
        if attribute == 'product':
            return {'value': {'value': "'product_code'"}}
        # Case 2
        if attribute in ['prod_qty',
                         'prod_unit_price',
                         'prod_sub_total',
                         'prod_discount',
                         'prod_weight',
                         'prod_net_price',
                         ]:
            return {'value': {'value': "'product_code',0.00"}}
        # Case 3
        if attribute in ['comp_sub_total',
                         'comp_sub_total_x']:
            return {'value': {'value': "['product_code','product_code2']|0.00"}
                    }
        # Case 4
        if attribute in ['amount_untaxed', 'amount_tax', 'amount_total']:
            return {'value': {'value': "0.00"}}

        # Case 5
        if attribute in ['pallet']:
            return {'value': {'value': "0.00"}}

        # Case 6
        if attribute in ['ship_address']:
            return {'value': {'value': "'city_name'"}}

        # Case 7
        if attribute in ['prod_pallet']:
            return {'value': {'value': "'product_code',0.00"}}

        return {}

    _columns = {
        'sequence': fields.integer('Sequence'),
        'attribute': fields.selection(ATTRIBUTES, 'Attribute', size=50,
                                      required=True),
        'comparator': fields.selection(COMPARATORS, 'Comparator',
                                       required=True),
        'value': fields.char('Value', size=100),
        'serialised_expr': fields.char('Expression', size=255),
        'promotion': fields.many2one('promos.rules', 'Promotion'),
        'stop_further': fields.boolean('Stop further checks')
    }

    _defaults = {
        'comparator': lambda * a: '==',
        'stop_further': lambda * a: '1'
    }

    def validate(self, cr, uid, vals, context=None):
        """
        Checks the validity
        """
        numerical_comparators = ['==', '!=', '<=', '<', '>', '>=']
        iterator_comparators = ['in', 'not in']
        attribute = vals['attribute']
        comparator = vals['comparator']
        value = vals['value']
        # Mismatch 1:
        if attribute in ['amount_untaxed',
                         'amount_tax',
                         'amount_total',
                         'prod_qty',
                         'prod_unit_price',
                         'prod_sub_total',
                         'prod_discount',
                         'prod_weight',
                         'prod_net_price',
                         'comp_sub_total',
                         'comp_sub_total_x',
                         'pallet'
                         ] and comparator not in numerical_comparators:
            raise Exception("Only %s can be used with %s"
                            % ",".join(numerical_comparators), attribute)
        # Mismatch 2:
        if attribute == 'product' and comparator not in iterator_comparators:
            raise Exception("Only %s can be used with Product Code"
                            % ",".join(iterator_comparators))
        # Mismatch 3:
        if attribute in ['prod_qty',
                         'prod_unit_price',
                         'prod_sub_total',
                         'prod_discount',
                         'prod_weight',
                         'prod_net_price',
                         'prod_pallet',
                         ]:
            try:
                product_code, quantity = value.split(",")
                if not (type(eval(product_code)) == str and
                        type(eval(quantity)) in [int, long, float]):
                    raise
            except:
                raise Exception("Value for %s combination is invalid\n"
                                "Eg for right format is `'PC312',120.50`"
                                % attribute)
        # Mismatch 4:
        if attribute in ['comp_sub_total',
                         'comp_sub_total_x']:
            try:
                product_codes_iter, quantity = value.split("|")
                if not (type(eval(product_codes_iter)) in [tuple, list] and
                        type(eval(quantity)) in [int, long, float]):
                    raise
            except:
                raise Exception(
                    "Value for computed subtotal combination is invalid\n"
                    "Eg for right format is `['code1,code2',..]|120.50`")

        # Mismarch 5_
        if attribute == 'ship_address' and comparator != '==':
            raise Exception("Only comparator '==' is allowed for this \
                             attribute")

        # After all validations say True
        return True

    def serialise(self, attribute, comparator, value):
        """
        Constructs an expression from the entered values
        which can be quickly evaluated
        @param attribute: attribute of promo expression
        @param comparator: Comparator used in promo expression.
        @param value: value according which attribute will be compared
        """

        res = "order.%s %s %s" % (attribute, comparator, value)

        if attribute == 'custom':
            return value
        if attribute == 'product':
            return '%s %s products' % (value,
                                       comparator)
        if attribute in ['prod_qty',
                         'prod_unit_price',
                         'prod_sub_total',
                         'prod_discount',
                         'prod_weight',
                         'prod_net_price',
                         ]:
            product_code, quantity = value.split(",")
            res = '(%s in products) and (%s["%s"] %s %s)' \
                  % (product_code, attribute, eval(product_code),
                     comparator, quantity)
        if attribute == 'comp_sub_total':
            product_codes_iter, value = value.split("|")
            res = """sum(
                [prod_sub_total.get(prod_code,0) for prod_code in %s]
                ) %s %s""" % (eval(product_codes_iter), comparator, value)
        if attribute == 'comp_sub_total_x':
            product_codes_iter, value = value.split("|")
            res = """(sum(prod_sub_total.values()) - sum(
                [prod_sub_total.get(prod_code,0) for prod_code in %s]
                )) %s %s""" % (eval(product_codes_iter), comparator, value)
        if attribute == 'pallet':
            res = """sum(prod_pallet.values()) %s %s""" % (comparator, value)
        if attribute == 'ship_address':
            res = """order.partner_shipping_id.city == %s""" % value
        if attribute == 'prod_pallet':
            product_code, qty = value.split(',')
            res = """prod_pallet.get(%s, 0.0) %s %s""" %\
                (product_code, comparator, qty)
        return res

    def evaluate(self, cr, uid,
                 expression, order, context=None):
        """
        Evaluates the expression in given environment
        @param cr: Database cr
        @param uid: ID of uid
        @param expression: Browse record of expression
        @param order: Browse Record of sale order
        @param context: Context(no direct use).
        @return: True if evaluation succeeded
        """
        products = []   # List of product Codes
        prod_qty = {}   # Dict of product_code:quantity
        prod_pallet = {}   # Dict of product_code:number_of_pallets
        prod_unit_price = {}
        prod_sub_total = {}
        prod_discount = {}
        prod_weight = {}
        # prod_net_price = {}
        prod_lines = {}

        for line in order.order_line.\
                filtered(lambda l: not l.product_id.no_promo):
            if line.product_id:
                product_code = line.product_id.code
                products.append(product_code)
                prod_lines[product_code] = line.product_id
                prod_qty[product_code] = \
                    prod_qty.get(product_code, 0.00) + line.product_uom_qty
#               prod_net_price[product_code] = prod_net_price.get(
#                                                    product_code, 0.00
#                                                    ) + line.price_net
                prod_unit_price[product_code] = \
                    prod_unit_price.get(product_code, 0.00) + line.price_unit
                prod_sub_total[product_code] = \
                    prod_sub_total.get(product_code, 0.00) + \
                    line.price_subtotal
                prod_discount[product_code] = \
                    prod_discount.get(product_code, 0.00) + line.discount
                prod_weight[product_code] = \
                    prod_weight.get(product_code, 0.00) + line.th_weight

                # Get number of entire pallets
                entire_pallets = 0
                packing = line.product_id.packaging_ids and \
                    line.product_id.packaging_ids[0] or False
                if packing and packing.ul.type == 'pallet' and packing.qty:
                    entire_pallets = line.product_uom_qty // packing.qty

                prod_pallet[product_code] = \
                    prod_pallet.get(product_code, 0.00) + entire_pallets
        return eval(expression.serialised_expr)

    def create(self, cr, uid, vals, context=None):
        """
        Serialise before save
        @param cr: Database cr
        @param uid: ID of uid
        @param vals: Values of current record.
        @param context: Context(no direct use).
        """
        try:
            self.validate(cr, uid, vals, context)
        except Exception, e:
            raise orm.except_orm("Invalid Expression", ustr(e))
        vals['serialised_expr'] = self.serialise(vals['attribute'],
                                                 vals['comparator'],
                                                 vals['value'])
        return super(PromotionsRulesConditionsExprs, self).\
            create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context):
        """
        Serialise before Write
        @param cr: Database cr
        @param uid: ID of uid
        @param ids: ID of current record.
        @param vals: Values of current record.
        @param context: Context(no direct use).
        """
        # Validate before save
        if type(ids) in [list, tuple] and ids:
            ids = ids[0]
        try:
            old_vals = self.read(cr, uid, ids,
                                 ['attribute', 'comparator', 'value'],
                                 context)
            old_vals.update(vals)
            'id' in old_vals and old_vals.pop('id')
            self.validate(cr, uid, old_vals, context)
        except Exception, e:
            raise orm.except_orm("Invalid Expression", ustr(e))
        # Only value may have changed and client gives only value
        vals = old_vals
        vals['serialised_expr'] = self.serialise(vals['attribute'],
                                                 vals['comparator'],
                                                 vals['value'])
        return super(PromotionsRulesConditionsExprs, self).\
            write(cr, uid, ids, vals, context)


class PromotionsRulesActions(orm.Model):
    "Promotions actions"
    _name = 'promos.rules.actions'
    _description = __doc__
    _rec_name = 'action_type'

    def on_change(self, cr, uid, ids=None, action_type=None, product_code=None,
                  arguments=None, context=None):
        """
        Sets the arguments as templates according to action_type
        @param cr: Database cr
        @param uid: ID of uid
        @param ids: ID of current record
        @param action_type: type of action to be taken
        @product_code: Product on which action will be taken.
                (Only in cases when attribute in expression is product.)
        @param arguments: Values that will be used in implementing of actions
        @param context: Context(no direct use).
        """
        if not action_type:
            return {}
        if arguments not in [False, "0.00", "1,1"] and product_code in \
            ["'product_code'", "'product_code_of_y'" "'product_code_x'",
             "'product_code_y'"]:
                return {}
        if action_type in ['prod_disc_perc', 'prod_disc_fix']:
            return {'value': {'product_code': "'product_code'",
                              'arguments': "0.00"}}
        if action_type in ['cart_disc_perc', 'cart_disc_fix']:
            return {'value': {'product_code': False,
                              'arguments': "0.00"}}
        if action_type in ['prod_x_get_y']:
            return {'value':
                    {'product_code': "'product_code_x','product_code_y'",
                     'arguments': "1,1"}}
        # Finally if nothing works
        return {}

    _columns = {
        'sequence': fields.integer('Sequence', required=True),
        'action_type': fields.selection(ACTION_TYPES, 'Action', required=True),
        'product_code': fields.char('Product Code', size=100),
        'arguments': fields.char('Arguments', size=100),
        'promotion': fields.many2one('promos.rules', 'Promotion'),
    }

    def create_line(self, cr, uid, vals, context):
        return self.pool.get('sale.order.line').create(cr, uid, vals, context)

    def action_prod_disc_perc(self, cr, uid, action, order, context=None):
        """
        Action for 'Discount % on Product'
        @param cr: Database cr
        @param uid: ID of uid
        @param action: Action to be taken on sale order
        @param order: sale order
        @param context: Context(no direct use).
        """
        order_line_obj = self.pool.get('sale.order.line')
        for order_line in order.order_line.\
                filtered(lambda l: not l.product_id.no_promo):
            if order_line.product_id.code == eval(action.product_code):
                return order_line_obj.\
                    write(cr, uid, order_line.id,
                          {'discount': eval(action.arguments),
                           'old_discount': order_line.discount}, context)

    def action_prod_disc_fix(self, cr, uid,
                             action, order, context=None):
        """
        Action for 'Fixed amount on Product'
        @param cr: Database cr
        @param uid: ID of uid
        @param action: Action to be taken on sale order
        @param order: sale order
        @param context: Context(no direct use).
        """
        # order_line_obj = self.pool.get('sale.order.line')
        product_obj = self.pool.get('product.product')
        line_name = '%s on %s' % (action.promotion.name,
                                  eval(action.product_code))
        domain = [('default_code', '=', eval(action.product_code))]
        product_id = product_obj.search(cr, uid, domain, context=context)
        if not product_id:
            raise Exception("No product with the product code")
        if len(product_id) > 1:
            raise Exception("Many products with same code")
        product = product_obj.browse(cr, uid, product_id[0], context)
        args = {
            'order_id': order.id,
            'name': line_name,
            'promotion_line': True,
            'price_unit': -eval(action.arguments),
            'product_uom_qty': 1,
            'product_uom': product.uom_id.id
        }
        self.create_line(cr, uid, args, context)
        return True

    def action_cart_disc_perc(self, cr, uid, action, order, context=None):
        """
        'Discount % on Sub Total'
        @param cr: Database cr
        @param uid: ID of uid
        @param action: Action to be taken on sale order
        @param order: sale order
        @param context: Context(no direct use).
        """
        args = {
            'order_id': order.id,
            'name': action.promotion.name,
            'price_unit': -(order.amount_untaxed * eval(action.arguments) /
                            100),
            'product_uom_qty': 1,
            'promotion_line': True,
            'product_uom': PRODUCT_UOM_ID
        }
        self.create_line(cr, uid, args, context)
        return True

    def action_cart_disc_fix(self, cr, uid, action, order, context=None):
        """
        'Fixed amount on Sub Total'
        @param cr: Database cr
        @param uid: ID of uid
        @param action: Action to be taken on sale order
        @param order: sale order
        @param context: Context(no direct use).
        """
        if action.action_type == 'cart_disc_fix':
            args = {
                'order_id': order.id,
                'name': action.promotion.name,
                'price_unit': -eval(action.arguments),
                'product_uom_qty': 1,
                'promotion_line': True,
                'product_uom': PRODUCT_UOM_ID
            }
            self.create_line(cr, uid, args, context)
            return True

    def create_y_line(self, cr, uid, action, order, quantity, product_id,
                      context=None):
        """
        Create new order line for product
        @param cr: Database cr
        @param uid: ID of uid
        @param action: Action to be taken on sale order
        @param order: sale order
        @param quantity: quantity of new free product
        @param product_id: product to be given free
        @param context: Context(no direct use).
        """
        product_obj = self.pool.get('product.product')
        product_y = product_obj.browse(cr, uid, product_id[0])
        vals = {
            'order_id': order.id,
            'product_id': product_y.id,
            'name': '[%s]%s (%s)' % (product_y.default_code,
                                     product_y.name,
                                     action.promotion.name),
            'price_unit': 0.00, 'promotion_line': True,
            'product_uom_qty': quantity,
            'product_uom': product_y.uom_id.id
        }
        self.create_line(cr, uid, vals, context)
        return True

    def action_prod_x_get_y(self, cr, uid, action, order, context=None):
        """
        'Buy X get Y free:[Only for integers]'
        @param cr: Database cr
        @param uid: ID of uid
        @param action: Action to be taken on sale order
        @param order: sale order
        @param context: Context(no direct use).

        Note: The function is too long because if it is split then there
                will a lot of arguments to be passed from one function to
                another. This might cause the function to get slow and
                hamper the coding standards.
        """
        product_obj = self.pool.get('product.product')

        prod_qty = {}
        # Get Product
        product_x_code, product_y_code = \
            [eval(code) for code in action.product_code.split(",")]
        product_id = product_obj.search(cr, uid,
                                        [('default_code', '=',
                                          product_y_code)], context=context)
        if not product_id:
            raise Exception("No product with the code for Y")
        if len(product_id) > 1:
            raise Exception("Many products with same code")
        # get Quantity
        qty_x, qty_y = [eval(arg) for arg in action.arguments.split(",")]
        # Build a dictionary of product_code to quantity
        for order_line in order.order_line.\
                filtered(lambda l: not l.product_id.no_promo):
            if order_line.product_id:
                product_code = order_line.product_id.default_code
                prod_qty[product_code] = \
                    prod_qty.\
                    get(product_code, 0.00) + order_line.product_uom_qty
        # Total number of free units of y to give
        qty_y_in_cart = prod_qty.get(product_y_code, 0)
        if product_x_code == product_y_code:
            diff_x_y = qty_y - qty_x
            tot_free_y = int(qty_y_in_cart / qty_x) * diff_x_y
        else:
            tot_free_y = int(qty_y_in_cart / qty_x) * qty_y

        if not tot_free_y:
            return True
        return self.create_y_line(cr, uid, action, order, tot_free_y,
                                  product_id, context)

    def action_line_prod_disc_perc(self, cr, uid,
                                   action, order, context=None):
        """
        Crea una nueva linea de cantidad 1 y precio_unitario el descuento
        sobre el subtotal del pedido
        """
        line_name = action.promotion.name

        obj_data = self.pool.get('ir.model.data')
        prod_id = obj_data.get_object_reference(cr, uid, 'sale_promotions',
                                                'product_discount')[1]
        for order_line in order.order_line.\
                filtered(lambda l: not l.product_id.no_promo):
            if not action.product_code or \
                    order_line.product_id.code == eval(action.product_code):
                disc = eval(action.arguments)
                args = {
                    'order_id': order.id,
                    'name': line_name,
                    'price_unit': -(order.amount_untaxed * disc / 100),
                    'product_uom_qty': 1,
                    'promotion_line': True,
                    'product_uom': order_line.product_uom.id,
                    'product_id': prod_id,
                    'tax_id': [(6, 0, [x.id for x in order_line.tax_id])]
                }
                self.create_line(cr, uid, args, context)
            return True

    def _create_lines_groped_by_price(self, cr, uid, action, order,
                                      selected_lines, context=None):
        """
        Crea lineas de descuento agrupandolas por precio, con decuento sobre
        precio unitario, y agrupándolas por cantidad.
        """
        group_dic = {}  # Agrupar lineas del mismo precio y producto
        obj_data = self.pool.get('ir.model.data')
        prod_id = obj_data.get_object_reference(cr, uid, 'sale_promotions',
                                                'product_discount')[1]
        for line in selected_lines:
            key = line.price_unit
            if key not in group_dic:
                group_dic[key] = [0.0, []]
            group_dic[key][0] += line.product_uom_qty
            group_dic[key][1] += line

        line_name = action.promotion.name
        for price in group_dic:
            qty = group_dic[price][0]
            lines = group_dic[price][1]
            disc = eval(action.arguments)
            taxes = set()
            for l in lines:
                for t in l.tax_id:
                    taxes.add(t.id)
            taxes = list(set(taxes))
            args = {
                'order_id': order.id,
                'name': line_name,
                'price_unit': -(price * disc / 100),
                'product_uom_qty': qty,
                'promotion_line': True,
                'product_uom': lines[0].product_uom.id,
                'product_id': prod_id,
                'tax_id': [(6, 0, taxes)],
                'orig_line_ids': [(6, 0, [x.id for x in lines])]
            }
            self.create_line(cr, uid, args, context)
        return

    def action_line_discount_group_price(self, cr, uid, action, order,
                                         context=None):
        """
        Crea una linea descuento con el descuento apñicado al precio unitario
        y la cantadid será la suma de las lineas implicadas. Se crea una linea
        descuento a mayores por cada linea implicada con un precio diferente
        """

        selected_lines = []
        restrict_codes = False
        if action.product_code:
            restrict_codes = action.product_code.replace("'", '').split(',')
        for line in order.order_line.\
                filtered(lambda l: not l.product_id.no_promo):
            if restrict_codes and line.product_id.code not in restrict_codes:
                continue
            selected_lines += line
        self._create_lines_groped_by_price(cr, uid, action, order,
                                           selected_lines, context)
        return

    def action_line_discount_mult_pallet(self, cr, uid, action, order,
                                         context=None):
        """
        Crea una linea descuento por cada linea que cumpla que hay un número
        de pallets, múltiplo de 1.
        """
        selected_lines = []
        for line in order.order_line.\
                filtered(lambda l: not l.product_id.no_promo):
            packing = line.product_id.packaging_ids \
                and line.product_id.packaging_ids[0] or False
            num_pallets = 0.0
            if packing and packing.ul.type == 'pallet' and packing.qty:
                num_pallets = line.product_uom_qty / packing.qty
            if not num_pallets or num_pallets % 1 != 0:
                continue

            selected_lines += line
        self._create_lines_groped_by_price(cr, uid, action, order,
                                           selected_lines, context)
        return

    def execute(self, cr, uid, action_id, order, context=None):
        """
        Executes the action into the order
        @param cr: Database cr
        @param uid: ID of uid
        @param action_id: Action to be taken on sale order
        @param order: sale order
        @param context: Context(no direct use).
        """
        # self.clear_existing_promotion_lines(cr, uid, order, context)
        action = self.browse(cr, uid, action_id, context)
        method_name = 'action_' + action.action_type
        return getattr(self, method_name).__call__(cr, uid, action,
                                                   order, context)

    def validate(self, cr, uid, vals, context):
        """
        Validates if the values are coherent with
        attribute
        @param cr: Database cr
        @param uid: ID of uid
        @param vals: Values of current record.
        @param context: Context(no direct use).
        """
        if vals['action_type'] in ['prod_disc_perc', 'prod_disc_fix']:
            if not type(eval(vals['product_code'])) == str:
                raise Exception("Invalid product code\nHas to be \
                                'product_code'")
            if not type(eval(vals['arguments'])) in [int, long, float]:
                raise Exception("Argument has to be numeric. eg: 10.00")

        if vals['action_type'] in ['cart_disc_perc', 'cart_disc_fix']:
            if vals['product_code']:
                raise Exception("Product code is not used in cart actions")
            if not type(eval(vals['arguments'])) in [int, long, float]:
                raise Exception("Argument has to be numeric. eg: 10.00")

        if vals['action_type'] in ['prod_x_get_y', ]:
            try:
                code_1, code_2 = vals['product_code'].split(",")
                assert (type(eval(code_1)) == str)
                assert (type(eval(code_2)) == str)
            except:
                raise Exception("Product codes have to be of form \
                                'product_x','product_y'")
            try:
                qty_1, qty_2 = vals['arguments'].split(',')
                assert (type(eval(qty_1)) in [int, long])
                assert (type(eval(qty_2)) in [int, long])
            except:
                raise Exception("Argument has to be qty of x,y eg.`1, 1`")

        return True

    def create(self, cr, uid, vals, context=None):
        """
        Validate before save
        @param cr: Database cr
        @param uid: ID of uid
        @param vals: Values of current record.
        @param context: Context(no direct use).
        """
        try:
            self.validate(cr, uid, vals, context)
        except Exception, e:
            raise orm.except_orm("Invalid Expression", ustr(e))
        return super(PromotionsRulesActions, self).create(cr, uid,
                                                          vals, context)

    def write(self, cr, uid, ids, vals, context):
        """
        Validate before Write
        @param cr: Database cr
        @param uid: ID of uid
        @param vals: Values of current record.
        @param context: Context(no direct use).
        """
        # Validate before save
        if type(ids) in [list, tuple] and ids:
            ids = ids[0]
        try:
            old_vals = self.read(cr, uid, ids,
                                 ['action_type', 'product_code', 'arguments'],
                                 context)
            old_vals.update(vals)
            'id' in old_vals and old_vals.pop('id')
            self.validate(cr, uid, old_vals, context)
        except Exception, e:
            raise orm.except_orm("Invalid Expression", ustr(e))
        # only value may have changed and client gives only value
        vals = old_vals
        return super(PromotionsRulesActions, self).write(cr, uid, ids,
                                                         vals, context)
