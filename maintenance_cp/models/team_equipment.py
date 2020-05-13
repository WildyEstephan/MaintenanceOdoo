from odoo import api, fields, models

class Employee(models.Model):
    _inherit = 'hr.employee'

    # This field is fill from Equipment Team
    team_id = fields.Many2one(comodel_name="maintenance.cp.team",
                                   string="Equipment Team",
                                   required=False, )

    # For Add this employee to a team by domain.
    # If It's checked It will appear in list for teams
    is_specialist = fields.Boolean(string="Specialist", )
    task_ids = fields.One2many(comodel_name="maintenance.cp.description.task", inverse_name="specialist_id",
                                    string="Tasks", required=False, )


# This model will help to management the employees
class EquipmentTeam(models.Model):
    _name = 'maintenance.cp.team'
    _rec_name = 'name'
    _description = 'Equipment Team'

    name = fields.Char(string="Name", required=True, )
    members_ids = fields.One2many(comodel_name="hr.employee",
                                    inverse_name="team_id",
                                    string="Members", required=True, )
    supervisor_id = fields.Many2one(comodel_name="hr.employee", string="Supervisor", required=True, )
    manager_id = fields.Many2one(comodel_name="hr.employee", string="Manager", required=True, )
    department_id = fields.Many2one(comodel_name="hr.department", string="Department", required=False, )
