from odoo import api, fields, models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    workorder_id = fields.Many2one(comodel_name="'maintenance.cp.workorder'",
                                   string="Work Order", required=False, )


