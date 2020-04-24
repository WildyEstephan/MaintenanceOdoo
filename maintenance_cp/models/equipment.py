
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
    team_id = fields.Many2one(comodel_name="maintenance.cp.team",
                              string="Equipment Team", required=True, )

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
    location_id = fields.Many2one(comodel_name="stock.location", string="Location", required=False, )
    importance = fields.Selection(string="Importance",
                             selection=[('0', 'General'),
                                        ('1', 'Important'),
                                        ('2', 'Very Important'),
                                        ('3', 'Critical'),
                                        ],
                             required=False, default='0')

    maintenance_date = fields.Datetime(string="Maintenance Date", required=False, )
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
