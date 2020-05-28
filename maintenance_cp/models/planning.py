from odoo import api, fields, models
from odoo.addons import decimal_precision as dp
from datetime import datetime, timedelta
from odoo import exceptions, _

class Planning(models.Model):
    _name = 'maintenance.planning'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _description = 'Planning Work Order'

    def default_currency(self):
        currency = self.env.user.company_id.currency_id
        return currency.id

    name = fields.Char(string="Sequence", required=False, )
    equipment_id = fields.Many2one(comodel_name="maintenance.cp.equipment", string="Equipment",
                                   required=True, )
    category_id = fields.Many2one(comodel_name="maintenance.cp.equipment.category",
                                  string="Category", related="equipment_id.category_id", )
    description_maintenance = fields.Text(string="Description for Maintenance", required=False, )

    need_breakdown = fields.Boolean(string="Breakdown", )

    # El tecnico introduce la fecha de culminacion.
    # Cuando se ejecute el inicio de la orden se llena el campo start_date.
    # Cuando se ejecute el termino de la orden se llena el campo end_date
    # y se calcula las horas que haya durado
    # Con este calculo se llena el campo end_hours
    start_date = fields.Datetime(string="Start Planning Date", required=True, )
    end_date = fields.Datetime(string="End Planning Date", required=False, )
    planned_end_hours = fields.Float(string="Planned End Hours", required=False, compute='_compute_planned_end_hours')

    frequency_exe = fields.Integer(string="Frequency Of Execution", required=True, )
    frequency_time = fields.Selection(string="Frequency Time",
                                      selection=[('day', 'Days'),
                                                   ('week', 'Weeks'),
                                                   ('month', 'Months'),
                                                   ('year', 'Years'),
                                                   ], required=True, default='day')

    # Especificar la seccion o secciones a dar mantenimiento
    # Esto ayudar a identificar las partes a trabajar
    section_ids = fields.Many2many(comodel_name="maintenance.cp.equipment.section",
                                     relation="section_planning_equipment_rel",
                                     column1="planning_id",
                                     column2="section_id", string="Sections",
                                   domain="[('equipment_id', '=', equipment_id)]" )

    parts_ids = fields.One2many(comodel_name="maintenance.planning.planned.parts",
                                    inverse_name="planning_id", string="Planned Parts", required=True, )
    service_ids = fields.One2many(comodel_name="maintenance.planning.service", inverse_name="planning_id",
                                  string="Services", required=True, )

    team_id = fields.Many2one(comodel_name="maintenance.cp.team",
                              string="Equipment Team", required=True, )

    state = fields.Selection(string="Status",
                             selection=[('draft', 'Draft'),
                                        ('approved', 'Approved'),
                                        ('started', 'Started'),
                                        ('ended', 'Ended'),
                                        ('cancel', 'Cancel'),
                                        ],
                             required=False, default="draft")

    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)

    task_ids = fields.One2many(comodel_name="maintenance.planning.task", inverse_name="planning_id", string="Tasks", required=False, )

    # workorder_ids = fields.One2many(comodel_name="maintenance.cp.workorder", inverse_name="planning_id", string="Work Orders", required=False, )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        required=False, default=default_currency)

    total_cost = fields.Float(
        string='Total Cost',
        required=False, compute='_compute_total_cost')

    @api.multi
    @api.depends('task_ids', 'parts_ids', 'service_ids')
    def _compute_total_cost(self):
        cost_task = 0.0
        cost_part = 0.0
        cost_service = 0.0

        for record in self:

            for task in record.task_ids:
                cost_task = cost_task + task.workforce_cost

            for part in record.parts_ids:
                cost_part = cost_part + part.total

            for service in record.service_ids:
                cost_service = cost_service + service.total

            record.total_cost = cost_part + cost_task + cost_service


    @api.one
    @api.depends('task_ids')
    def _compute_planned_end_hours(self):
        """
        @api.depends() should contain all fields that will be used in the calculations.
        """
        total = 0.0

        for task in self.task_ids:
            total = total + task.hours

        self.planned_end_hours = total

    @api.model
    def update_maintenance_date(self):

        records = self.env['maintenance.planning'].search([('state', '=', 'started')])

        for rec in records:

            today = datetime.now()
            today_str = today.strftime('%Y-%m-%d')
            day_man = ''
            new_date = ''

            day_start_str = rec.start_date.split(' ')[0]
            day_start = datetime.strptime(day_start_str, '%Y-%m-%d')



            if rec.equipment_id.maintenance_date:
                day_man = rec.equipment_id.maintenance_date.split(' ')[0]

                if (not today_str == day_man) or (today_str < day_man):
                    if rec.frequency_time == 'day':
                        new_date = datetime.now() + timedelta(days=rec.frequency_exe)
                    elif rec.frequency_time == 'week':
                        new_date = datetime.now() + timedelta(weeks=rec.frequency_exe)
                    elif rec.frequency_time == 'month':
                        new_date = datetime.now() + timedelta(days=30 * rec.frequency_exe)
                    else:
                        new_date = datetime.now() + timedelta(days=365 * rec.frequency_exe)

                    rec.equipment_id.maintenance_date = new_date
            else:

                if rec.frequency_time == 'day':
                    new_date = day_start + timedelta(days=rec.frequency_exe)
                elif rec.frequency_time == 'week':
                    new_date = day_start + timedelta(weeks=rec.frequency_exe)
                elif rec.frequency_time == 'month':
                    new_date = day_start + timedelta(days=30 * rec.frequency_exe)
                else:
                    new_date = day_start + timedelta(days=365 * rec.frequency_exe)

                rec.equipment_id.maintenance_date = new_date


    @api.model
    def end_all_planning(self):
        today = datetime.now()

        records = self.env['maintenance.planning'].search([('state', '=', 'started'), ('end_date', '=', today)])

        records.end_planning()

    @api.model
    def execute_all_planning(self):

        records = self.env['maintenance.planning'].search([('state', '=', 'started')])

        for rec in records:

            today = datetime.now()
            today_str = today.strftime('%Y-%m-%d')
            day_man = ''

            if rec.equipment_id.maintenance_date:

                day_man = rec.equipment_id.maintenance_date.split(' ')[0]

                if today_str == day_man:
                    rec.execute_maintenance()

    @api.multi
    def end_planning(self):
        self.state = 'ended'



    def approve_this(self):

        self.state = 'approved'

        if not self.task_ids:
            raise exceptions.UserError(_('You Has Not Tasks For This Planning Of Maintenance'))

    @api.multi
    def execute_maintenance(self):

        today = datetime.now()

        if not self.equipment_id.maintenance_date:
            self.equipment_id.maintenance_date = today

        workorder = self.env['maintenance.cp.workorder'].create(
            {
                'equipment_id': self.equipment_id.id,
                'type_maintenance': 'preventive',
                'description_problem': "Maintenance Preventive",
                'need_breakdown': self.need_breakdown,
                # 'planned_end_hours': self.planned_end_hours,
                'state': 'send',
                'planning_id': self.id
            }
        )

        workorder.message_post_with_view('mail.message_origin_link',
                    values={'self': workorder, 'origin': self},
                    subtype_id=self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note'))

        parts = []

        services = []

        for p in self.parts_ids:
            self.env['maintenance.cp.planned.parts'].create(
                {
                    'product_id': p.product_id.id,
                    'product_qty': p.product_qty,
                    'estimated_cost': p.estimated_cost,
                    'name': p.name,
                    'workorder_id': workorder.id,
                    'vendor_id': p.vendor_id.id
                }
            )

        for s in self.service_ids:
            self.env['maintenance.cp.service'].create(
                {
                    'product_id': s.product_id.id,
                    'estimated_cost': s.estimated_cost,
                    'vendor_id': s.vendor_id.id,
                    'name': 'Description',
                    'workorder_id': workorder.id,
                }
            )

        task = []

        # task_id
        # hours

        for t in self.task_ids:
            self.env['maintenance.cp.description.task'].create(
                {
                    'description': t.description,
                    'type_workforce_id': t.task_id.type_workforce_id.id,
                    'task_id': t.task_id.id,
                    'sequence': t.sequence,
                    'workorder_id':workorder.id,
                    'planned_end_hours': t.hours
                }
            )
            # description
            # type_workforce_id
            # task_id
            # workorder_id
            # planned_end_hours
            # team_id

        # equipment_id
        # type_maintenance
        # description_problem
        # need_breakdown
        # planned_end_hours
        # section_ids
        # parts_ids
        # service_ids
        # team_id
        # state
        # description_ids

            self.sudo().write({'state': 'started'})

    @api.model
    def create(self, values):
        # Add code here
        ID = super(Planning, self).create(values)

        sequence = self.env['ir.sequence'].next_by_code(
            'workorder.planning')
        ID.name = sequence

        ID.team_id = ID.equipment_id.team_id

        return ID

class PlanningTask(models.Model):
    _name = 'maintenance.planning.task'
    _description = 'Planning Task'
    
    def default_currency(self):
        currency = self.env.user.company_id.currency_id
        return currency.id

    sequence = fields.Integer(string="Sequence", required=False, )

    planning_id = fields.Many2one(comodel_name="maintenance.planning",
                                   string="Planning", required=False, )

    task_id = fields.Many2one(comodel_name="maintenance.cp.task", string="Task", required=True, domain="[('category_id', '=', category_id)]")
    hours = fields.Float(string="Hours Planned",  required=False, )
    description = fields.Char(string="Description", required=False, )

    workforce_cost = fields.Float(string="Workforce Cost", required=False, compute='_compute_workforce_cost',
                                  store=True)
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        required=False, default=default_currency)

    equipment_id = fields.Many2one(comodel_name="maintenance.cp.equipment", string="Equipment",
                                   store=True, related="planning_id.equipment_id")
    category_id = fields.Many2one(comodel_name="maintenance.cp.equipment.category",
                                  string="Category",)
                                  # related="planning_id.category_id", store=True)


    @api.multi
    @api.depends('task_id')
    def _compute_workforce_cost(self):

        for record in self:

            tasks = self.env['maintenance.cp.description.task'].search([('task_id', '=', record.task_id.id)])
            cost_ave = 0.0
            cost = 0.0
            for task in tasks:
                cost = cost + task.workforce_cost

            try:

                cost_ave = cost / len(tasks)
            except ZeroDivisionError:
                cost_ave = 0

            record.workforce_cost = cost_ave


    @api.onchange('task_id')
    def _onchange_task_id(self):
        for record in self:
            record.hours = record.task_id.planned_end_hours



class PlannedParts(models.Model):
    _name = 'maintenance.planning.planned.parts'
    _description = 'Planned Parts'

    def default_currency(self):
        currency = self.env.user.company_id.currency_id
        return currency.id

    name = fields.Char(string="Description", required=True, )
    planning_id = fields.Many2one(comodel_name="maintenance.planning",
                                   string="Work Order", required=False, )
    product_id = fields.Many2one(comodel_name="product.product", string="Product",
                                 required=True, domain="[('is_part', '=', 'True')]")
    product_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'),
                               required=True)
    estimated_cost = fields.Float(
        string='Estimated Cost',
        required=True)
    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)
    vendor_id = fields.Many2one(comodel_name="res.partner", string="Suggested Vendor", required=True,
                                domain=[('supplier', '=', True)])
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        required=False, default=default_currency)

    total = fields.Float(
        string='Total', 
        required=False, compute='_compute_total')
    
    @api.multi
    @api.depends('estimated_cost', 'product_qty')
    def _compute_total(self):

        for record in self:
            record.total = record.product_qty * record.estimated_cost
        

class Service(models.Model):
    _name = 'maintenance.planning.service'
    _rec_name = 'name'
    _description = 'Service Maintenance'

    def default_currency(self):
        currency = self.env.user.company_id.currency_id
        return currency.id

    name = fields.Char(string="Description", required=True, )
    planning_id = fields.Many2one(comodel_name="maintenance.planning", string="Planning", required=False, )
    product_id = fields.Many2one(comodel_name="product.product", string="Service",
                                 required=True, domain=[('is_workforce', '=', True)])
    estimated_cost = fields.Float(string='Estimated Cost', required=True,
                                  digits=dp.get_precision('Product Price'))
    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)
    vendor_id = fields.Many2one(comodel_name="res.partner", string="Suggested Vendor", required=True,
                                domain=[('supplier', '=', True)])

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        required=False, default=default_currency)

    total = fields.Float(
        string='Total',
        required=False, compute='_compute_total')

    @api.multi
    @api.depends('estimated_cost')
    def _compute_total(self):
        for record in self:
            record.total = record.estimated_cost
