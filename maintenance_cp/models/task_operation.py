from odoo import api, fields, models, tools, _
from odoo.addons import decimal_precision as dp
from datetime import datetime, timedelta
from odoo.tools import float_compare, pycompat

# Type of Workforce
class TypeWorkforce(models.Model):
    _name = 'maintenance.cp.type.workforce'
    _rec_name = 'name'
    _description = 'Maintenance Type Workforce'

    name = fields.Char(string="Name", required=True, )
    description = fields.Text(string="Description", required=False, )
    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)

# Type of Workforce in Employee
class Employee(models.Model):
    _inherit = 'hr.employee'

    type_workforce_id = fields.Many2one(comodel_name="maintenance.cp.type.workforce",
                                   string="Type of Workforce", required=False, )
# Tool
class Tool(models.Model):
    _name = 'maintenance.cp.tool'
    _rec_name = 'name'
    _description = 'Maintenance Tools'

    name = fields.Char(string="Name of Tool", required=True, )
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

    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)

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




# Operations
class Operation(models.Model):
    _name = 'maintenance.cp.operation'
    _rec_name = 'name'
    _description = 'Mantenance Operation'
    _order = 'sequence'

    name = fields.Char(string="Description", required=True, )
    documentation_file = fields.Binary(string="Documentation", )
    file_name = fields.Char(string="Description", required=False, )
    task_id = fields.Many2one(comodel_name="maintenance.cp.task", string="Task", required=False, )
    sequence = fields.Integer(string="Sequence", required=True, )
    tool_id = fields.Many2one(comodel_name="maintenance.cp.tool", string="Tool", required=False, )

    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)

# Tasks
class Task(models.Model):
    _name = 'maintenance.cp.task'
    _rec_name = 'name'
    _description = 'Maintenance Task'

    name = fields.Char(string="Name of Task", required=True, )
    type_workforce_id = fields.Many2one(comodel_name="maintenance.cp.type.workforce",
                                        string="Type of Workforce", required=False, )

    operation_ids = fields.One2many(comodel_name="maintenance.cp.operation",
                                    inverse_name="task_id",
                                    string="Operations", required=False, )
    planned_end_hours = fields.Float(string="Planned End Hours", required=False, )

    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)
