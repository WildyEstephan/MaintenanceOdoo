from odoo import api, fields, models

# Hereramos de product.template para
# agreagr campos que nos ayudaran hacer filtros

# Agrego puede ser una parte
# Agrego puede ser servicio de mano de hora
#     * Si el tipo de producto es servicio entonces aparece el campo check 'mano de obra'

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Check para saber si es una parte de equipo
    is_part = fields.Boolean(string="Maintenance Consumable", )

    # Check para saber si es una mano de obra
    is_workforce = fields.Boolean(string="Is Workforce",  )

    equipment_id = fields.Many2one(
        comodel_name='maintenance.cp.equipment',
        string='Equipment',
        required=False)

