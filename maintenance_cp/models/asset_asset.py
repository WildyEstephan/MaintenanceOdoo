from odoo import api, fields, models

class Asset(models.Model):
    _inherit = 'account.asset.asset'

    equipment_id = fields.Many2one(comodel_name="maintenance.cp.equipment",
                                   string="Equipment", required=False, )
    code = fields.Char(string='Reference', size=32, required=True, readonly=True, states={'draft': [('readonly', False)]})

    @api.model
    def create(self, values):
        # Add code here
        ID = super(Asset, self).create(values)

        equipment_id = ID.env['maintenance.cp.equipment'].create({
            'name': ID.name,
            'number_equipment': ID.code,
            'standard_price': ID.value
        })

        ID.equipment_id = equipment_id

        return ID
