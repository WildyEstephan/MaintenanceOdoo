from odoo import api, fields, models, tools


class WorkOrder(models.Model):
    _name = 'maintenance.cp.reporting'
    _auto = False

    name = fields.Char(string="Name", required=False, )
    equipment_id = fields.Many2one(comodel_name="maintenance.cp.equipment", string="Equipment",
                                   required=False, )
    type_maintenance = fields.Selection(string="Type of Maintenance", selection=[('corrective', 'Corrective'),
                                                   ('preventive', 'Preventive'), ],
                             required=False, default='corrective')
    need_breakdown = fields.Boolean(string="Breakdown", )
    start_date = fields.Datetime(string="Start Date", required=False, )
    end_date = fields.Datetime(string="End Date", required=False, )
    planned_end_date = fields.Datetime(string="Planned End Date", required=False, )
    planned_end_hours = fields.Float(string="Planned End Hours", required=False, )
    end_hours = fields.Float(string="End Hours",  required=False, )

    time_effectiveness = fields.Selection(string="Time Effectiveness",
                                          selection=[('mild', 'Mild'), ('normal', 'Normal'), ('optimum', 'Optimum'),
                                                     ], required=False, )
    effectiveness = fields.Integer(string="Effectiveness %", required=False, )
    specialist_id = fields.Many2one(comodel_name="hr.employee", string="Responsable", required=False, )
    team_id = fields.Many2one(comodel_name="maintenance.cp.team",
                              string="Equipment Team", required=False, )

    state = fields.Selection(string="Status",
                             selection=[('request', 'Request'),
                                        ('send', 'Send'),
                                        ('approved', 'Approved'),
                                        ('started', 'Started'),
                                        ('ended', 'Ended'),
                                        ('cancel', 'Cancel'),
                                        ],
                             required=False,)

    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)
    type_workforce_id = fields.Many2one(comodel_name="maintenance.cp.type.workforce",
                                        string="Type of Workforce", required=True, )
    task_id = fields.Many2one(comodel_name="maintenance.cp.task", string="Task", required=True,
                              domain="[('type_workforce_id', '=', type_workforce_id)]")

    workorder_id = fields.Many2one(comodel_name="maintenance.cp.workorder", string="Work Order", required=False, )

    # user_id = fields.Many2one(comodel_name="res.users", string="User", required=False, )
    # workforce_cost = fields.Float(string="Workforce Cost",  required=False, )

    def _select(self):
        select_str = """
        mt.id as id, mt.equipment_id as equipment_id, mt.type_maintenance as type_maintenance,
        mt.need_breakdown as need_breakdown, mw.start_date as start_date, mw.end_date, mw.planned_end_date as planned_end_date,
        mt.planned_end_hours as planned_end_hours, mt.end_hours as end_hours, mw.time_effectiveness as time_effectiveness,
        mw.effectiveness as effectiveness, mt.specialist_id as specialist_id, mt.team_id as team_id, mt.state as state,
        mt.type_workforce_id as type_workforce_id, mt.task_id as task_id, mt.workorder_id as workorder_id, mt.company_id as company_id
        """
        return select_str

    def _from(self):
        from_str = """
        maintenance_cp_description_task mt join maintenance_cp_workorder mw on (mt.workorder_id=mw.id)
         """
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
               );""" % (self._table, self._select(), self._from()))

        # self._group_by()