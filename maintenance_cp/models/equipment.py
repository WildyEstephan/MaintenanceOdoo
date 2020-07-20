
import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from odoo.osv import expression

from odoo.addons import decimal_precision as dp

from odoo.tools import float_compare, pycompat

class Section(models.Model):
    _name = 'maintenance.cp.equipment.section'
    _rec_name = 'name'
    _description = 'Section Equipment'

    name = fields.Char(string="Name of Section", required=True, )
    equipment_id = fields.Many2one(comodel_name="maintenance.cp.equipment", string="", required=False, )
    is_general = fields.Boolean(string="General",  )


# Crear categoria de equipos
class EquipmentCategory(models.Model):
    _name = 'maintenance.cp.equipment.category'
    _rec_name = 'name'
    _description = 'Equipment Category'

    name = fields.Char(string="Name", required=True, )
    description = fields.Text(string="Description", required=False, )
    # team_id = fields.Many2one(comodel_name="maintenance.cp.team",
    #                           string="Equipment Team", required=True, )

    _sql_constraints = [('equipment_category_uniq', 'UNIQUE(name)', "You Can't Use This Name Because It's Exist")]

class Location(models.Model):
    _name = 'maintenance.cp.equipment.location'
    _rec_name = 'name'
    _description = 'Location Of Equipment'

    name = fields.Char(string="Name", required=True, index=True)
    ref = fields.Char(string='Internal Reference', index=True)
    active = fields.Boolean(default=True)
    street = fields.Char(string="Street", required=False, )
    street2 = fields.Char(string="Street 2", required=False, )
    zip = fields.Char(string="Zip", required=False, )
    city = fields.Char(string="City", required=False, )
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict')
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)

class Measure(models.Model):
    _name = 'maintenance.measure'
    _description = 'Measure'
    _order = 'date desc'

    equipment_id = fields.Many2one(
        comodel_name='maintenance.cp.equipment',
        string='Equipment',
        required=False)
    date = fields.Date(
        string='Date',
        required=True)
    value1 = fields.Float(
        string='Value 1',
        required=True)
    value2 = fields.Float(
        string='Value 2',
        required=True)
    total = fields.Float(
        string='Total',
        required=False, )
    type = fields.Selection(
        string='Type',
        selection=[('odometer', 'Odometer'),
                   ('horometry', 'Horometry'), ],
        required=False, default='odometer')

    @api.multi
    @api.depends('equipment_id', 'date', 'value1', 'value2', 'type')
    def _compute_total(self):

        for rec in self:
            if rec.type == 'odometer':
                end_odometer = self.env['maintenance.measure'].search([('type', '=', 'odometer'),
                                                                       ('equipment_id', '=', rec.equipment_id.id)],
                                                                      limit=1)
                total = rec.value1 - rec.value2

                rec.total = end_odometer.total + total

            elif rec.type == 'horometry':
                end_horometry = self.env['maintenance.measure'].search([('type', '=', 'horometry'),
                                                                       ('equipment_id', '=', rec.equipment_id.id)],
                                                                      limit=1)

                total = rec.value1 - rec.value2

                rec.total = end_horometry.total + total


# Crear equipos conectados con activos
class Equipment(models.Model):
    _name = 'maintenance.cp.equipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _description = 'Equipment'

    name = fields.Char(string="Name  of Equipment", required=True, )
    image_variant = fields.Binary(
        "Variant Image", attachment=True,
        help="This field holds the image used as image for the product variant, limited to 1024x1024px.")
    image = fields.Binary(
        "Big-sized image", compute='_compute_images', inverse='_set_image',
        help="Image of the product variant (Big-sized image of product template if false). It is automatically "
             "resized as a 1024x1024px image, with aspect ratio preserved.")
    image_small = fields.Binary(
        "Small-sized image", compute='_compute_images', inverse='_set_image_small',
        help="Image of the product variant (Small-sized image of product template if false).")
    image_medium = fields.Binary(
        "Medium-sized image", compute='_compute_images', inverse='_set_image_medium',
        help="Image of the product variant (Medium-sized image of product template if false).")

    category_id = fields.Many2one(comodel_name="maintenance.cp.equipment.category",
                                   string="Category", required=False, )
    location_id = fields.Many2one(comodel_name="maintenance.cp.equipment.location", string="Location", required=False, )
    importance = fields.Selection(string="Importance",
                             selection=[('0', 'General'),
                                        ('1', 'Important'),
                                        ('2', 'Very Important'),
                                        ('3', 'Critical'),
                                        ],
                             required=False, default='0')

    maintenance_date = fields.Date(string="Last Maintenance", required=False, )
    active = fields.Boolean(string="Active", default=True)
    number_equipment = fields.Char(string="Number of Equipment", required=True, )
    model_equipment = fields.Char(string="Model", required=False, )
    serial_number = fields.Char(string="Serial No.", required=False, )
    vendor_id = fields.Many2one(comodel_name="res.partner",
                                   string="Vendor", required=False, domain="[('supplier', '=', True)]")
    manufacter_id = fields.Many2one(comodel_name="res.partner",
                                string="Manufacter",
                                    required=False, domain="[('supplier', '=', True)]")
    warranty_start = fields.Date(string="Warranty Start", required=False, )
    warranty_end = fields.Date(string="Warranty End", required=False, )
    purchase_date = fields.Date(string="Purchase Date", required=False, )
    team_id = fields.Many2one(comodel_name="maintenance.cp.team",
                              string="Equipment Team", required=False, )
    standard_price = fields.Float(
        'Cost', company_dependent=True,
        digits=dp.get_precision('Product Price'),
        groups="base.group_user",
        help="Cost used for stock valuation in standard price and as a first price to set in average/fifo. "
             "Also used as a base price for pricelists. "
             "Expressed in the default unit of measure of the product.")
    asset_id = fields.Many2one(comodel_name="account.asset.asset",
                                   string="Asset",
                                   required=False, )
    section_ids = fields.One2many(comodel_name="maintenance.cp.equipment.section",
                                  inverse_name="equipment_id", string="Sections", required=True, )
    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)
    workorder_ids = fields.One2many(comodel_name="maintenance.cp.workorder",
                                    inverse_name="equipment_id", string="Work Orders", required=False, )
    workorder_count = fields.Integer(string="Receptions Count", compute='_compute_workorder_count', )

    planning_ids = fields.One2many(comodel_name="maintenance.planning",
                                    inverse_name="equipment_id", string="Maintenances", required=False, )
    planning_count = fields.Integer(string="Receptions Count", compute='_compute_planning_count', )
    metric_type = fields.Selection(
        string='Metric Type',
        selection=[('odometer', 'Odometer'),
                   ('horometry', 'Horometry'), ],
        required=True, default='odometer')
    metrics_ids = fields.One2many(
        comodel_name='maintenance.measure',
        inverse_name='equipment_id',
        string='Metrics',
        required=False, domain=[('type', '=', 'odometer'), ])
    metrics_horo_ids = fields.One2many(
        comodel_name='maintenance.measure',
        inverse_name='equipment_id',
        string='Metrics',
        required=False, domain=[('type', '=', 'horometry' ), ])

    def add_metric(self):

        view = self.env.ref('maintenance_cp.metrics_action')
        # wiz = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, self.id)]})

        action = {}

        if self.metric_type == 'odometer':
            conx = {
                'equipment_id': self.id,
                'type': 'odometer'
            }

            action = {
                'name': _('Odometer'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'maintenance.measure',
                'views': 'form',
                'target': 'new',
                'context': conx,
            }
        elif self.metric_type == 'horometry':
            conx = {
                'equipment_id': self.id,
                'type': 'horometry'
            }

            action = {
                'name': _('Horometry'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'maintenance.measure',
                'views': 'form',
                'target': 'new',
                'context': conx,
            }

        return action

    @api.one
    @api.depends('workorder_count')
    def _compute_workorder_count(self):
        """
        @api.depends() should contain all fields that will be used in the calculations.
        """
        self.workorder_count = len(self.workorder_ids)

    @api.one
    @api.depends('planning_count')
    def _compute_planning_count(self):
        """
        @api.depends() should contain all fields that will be used in the calculations.
        """
        self.planning_count = len(self.planning_ids)


    @api.onchange('asset_id')
    def _onchange_asset_id(self):

        if self.asset_id:
            self.asset_id.equipment_id = self.id

    @api.one
    @api.depends('image_variant')
    def _compute_images(self):
        if self._context.get('bin_size'):
            self.image_medium = self.image_variant
            self.image_small = self.image_variant
            self.image = self.image_variant
        else:
            resized_images = tools.image_get_resized_images(self.image_variant, return_big=True,
                                                            avoid_resize_medium=True)
            self.image_medium = resized_images['image_medium']
            self.image_small = resized_images['image_small']
            self.image = resized_images['image']

    @api.one
    def _set_image(self):
        self._set_image_value(self.image)

    @api.one
    def _set_image_medium(self):
        self._set_image_value(self.image_medium)

    @api.one
    def _set_image_small(self):
        self._set_image_value(self.image_small)

    @api.one
    def _set_image_value(self, value):
        if isinstance(value, pycompat.text_type):
            value = value.encode('ascii')
        image = tools.image_resize_image_big(value)
        self.image_variant = image
