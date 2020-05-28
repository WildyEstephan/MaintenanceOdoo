from odoo import fields, models, api, tools


class ModelName (models.Model):
    _name = 'maintenance.cost.report'
    _description = 'Maintenance Cost Report'
    _auto = False

    name = fields.Many2one(comodel_name="maintenance.cp.workorder", string="Work Order", required=False,)
    type_maintenance = fields.Selection(string="Type of Maintenance",
                                        selection=[('corrective', 'Corrective'),
                                                   ('preventive', 'Preventive'), ],)
    equipment_id = fields.Many2one(comodel_name="maintenance.cp.equipment", string="Equipment",
                                   required=False, )
    category_id = fields.Many2one(comodel_name="maintenance.cp.equipment.category",
                                  string="Category", required=False,)
    start_date = fields.Datetime(string="Start Date", required=False, )
    end_date = fields.Datetime(string="End Date", required=False, )
    # task_id = fields.Many2one(comodel_name="maintenance.cp.task", string="Task", required=False, )
    workforce_cost_total = fields.Float(string="Workforce Cost Total", required=False, )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        required=False, )
    planned_end_date = fields.Datetime(string="Planned End Date", required=False, )
    planned_end_hours = fields.Float(string="Planned End Hours", required=False, compute='_compute_planned_end_hours')
    end_hours = fields.Float(string="End Hours", required=False, )
    cost_service = fields.Float(string='Estimated Cost Services', required=False, )
    cost_part = fields.Float(string='Estimated Cost Parts', required=False, )
    cost_task = fields.Float(string='Estimated Cost Tasks', required=False,)
    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,)
    state = fields.Selection(string="Status",
                             selection=[('request', 'Request'),
                                        ('send', 'Send'),
                                        ('approved', 'Approved'),
                                        ('started', 'Started'),
                                        ('ended', 'Ended'),
                                        ('cancel', 'Cancel'),
                                        ],
                             required=False, )

    def _select(self):
        select_str = """
        wo.id as id, wo.workorder_id as name, wo.type_maintenance as type_maintenance, 
        wo.equipment_id as equipment_id, wo.category_id as category_id, 
        wo.start_date as start_date, wo.end_date as end_date, wo.workforce_cost_total as workforce_cost_total, 
        wo.currency_id as currency_id, wo.planned_end_date as planned_end_date, 
        wo.planned_end_hours as planned_end_hours, wo.end_hours as end_hours, 
        wo.cost_service as cost_service, wo.cost_part as cost_part, wo.cost_task as cost_task, 
        wo.state as state, wo.company_id as company_id"""
        return select_str

    def _from(self):
        from_str = """maintenance_cp_workorder as wo"""
        return from_str

    # def _group_by(self):
    #     group_by_str = """
    #         group by emp.id,psl.total,ps.date_from, ps.date_to, ps.state,jb.id,dp.id,cmp.id
    #     """
    #     return group_by_str

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as ( SELECT
               %s
               FROM %s
               )""" % (self._table, self._select(), self._from()))
    


