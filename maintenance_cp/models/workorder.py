from odoo import api, fields, models
from odoo.addons import decimal_precision as dp
from datetime import datetime, timedelta, time
from dateutil.relativedelta import relativedelta



from odoo import exceptions, _

class WorkOrder(models.Model):
    _name = 'maintenance.cp.workorder'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Equipment Work Order'

    name = fields.Char(string="Sequence", required=False, )
    equipment_id = fields.Many2one(comodel_name="maintenance.cp.equipment", string="Equipment",
                                   required=True, )
    category_id = fields.Many2one(comodel_name="maintenance.cp.equipment.category",
                                  string="Category", related="equipment_id.category_id", )
    location_id = fields.Many2one(comodel_name="maintenance.cp.equipment.location",
                                  string="Location", related="equipment_id.location_id", )
    type_maintenance = fields.Selection(string="Type of Maintenance", selection=[('corrective', 'Corrective'),
                                                   ('preventive', 'Preventive'), ],
                             required=False, default='corrective')
    description_maintenance = fields.Text(string="Description for Maintenance", required=False, )
    description_problem = fields.Text(string="Description Problem", required=True, )

    need_breakdown = fields.Boolean(string="Breakdown", )

    # El tecnico introduce la fecha de culminacion.
    # Cuando se ejecute el inicio de la orden se llena el campo start_date.
    # Cuando se ejecute el termino de la orden se llena el campo end_date
    # y se calcula las horas que haya durado
    # Con este calculo se llena el campo end_hours
    start_date = fields.Datetime(string="Start Date", required=False, )
    end_date = fields.Datetime(string="End Date", required=False, )
    planned_end_date = fields.Datetime(string="Planned End Date", required=False, )
    planned_end_hours = fields.Float(string="Planned End Hours", required=False, compute='_compute_planned_end_hours')
    end_hours = fields.Float(string="End Hours",  required=False, )

    time_effectiveness = fields.Selection(string="Time Effectiveness",
                                          selection=[('mild', 'Mild'), ('normal', 'Normal'), ('optimum', 'Optimum'),
                                                     ], required=False, )
    effectiveness = fields.Integer(string="Effectiveness %", required=False, )

    # El encargado de la orden de trabajo
    # Este campo sera llenado con el tecnico que tenga menos horas planeadas en sus ordenes de trabajo.
    # Si existe mas de un tecnico que cumple con la primera condicion se elige quien tenga mayor efectividad
    # de entrega a tiempo
    specialist_id = fields.Many2one(comodel_name="hr.employee", string="Responsable", required=False, )

    # Especificar la seccion o secciones a dar mantenimiento
    # Esto ayudar a identificar las partes a trabajar
    section_ids = fields.Many2many(comodel_name="maintenance.cp.equipment.section",
                                     relation="section_workorder_equipment_rel",
                                     column1="workorder_id",
                                     column2="section_id", string="Sections",
                                   domain="[('equipment_id', '=', equipment_id)]" )

    parts_ids = fields.One2many(comodel_name="maintenance.cp.planned.parts",
                                    inverse_name="workorder_id", string="Planned Parts", required=False, )
    service_ids = fields.One2many(comodel_name="maintenance.cp.service", inverse_name="workorder_id", string="Services", required=False, )

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
                             required=False, default="request")

    description_ids = fields.One2many(comodel_name="maintenance.cp.description.task", inverse_name="workorder_id", string="Description Of Maintenance", required=False, )

    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)
    is_checked = fields.Boolean(string="Task checked", )

    # planning_id = fields.Many2one(comodel_name="maintenance.planning", string="Planning", required=False, )

    def delete_task_parts(self):

        parts = self.env['maintenance.cp.planned.parts'].search([('task_id', '=', True), ('workorder_id', '=', self.id)])
        parts.unlink()

    @api.multi
    def check_task_parts(self):

        for description in self.description_ids:
            for part in description.task_id.parts_ids:
                self.env['maintenance.cp.planned.parts'].create(
                    {
                        'product_id': part.product_id.id,
                        'product_qty': part.product_qty,
                        'name': part.name,
                        'workorder_id': self.id,
                        'vendor_id': part.vendor_id.id,
                        'task_id': part.task_id.id
                    }
                )

        self.is_checked = True

    @api.one
    @api.depends('description_ids')
    def _compute_planned_end_hours(self):
        """
        @api.depends() should contain all fields that will be used in the calculations.
        """
        total = 0.0

        for desc in self.description_ids:
            total = total + desc.planned_end_hours

        self.planned_end_hours = total


    # def add_followers(self):
    #
    #     list_followers = [self.specialist_id.id or 0, self.team_id.supervisor_id.id, self.team_id.manager_id.id]
    #
    #     self.message_subscribe_users(list_followers)

    # def send_message(self):
    #     message = '''<div class="res.users"><a href="#" class="o_redirect" data-oe-id="%s">@%s</a>, <a href="#" class="o_redirect" data-oe-id="%s">@%s</a> and <a href="#" class="o_redirect" data-oe-id="%s">@%s</a>, you have a new request</div>''' \
    #               % (self.specialist_id.user_id.id, self.specialist_id.user_id.name,self.team_id.supervisor_id.user_id.id, self.team_id.supervisor_id.user_id.name, self.team_id.manager_id.user_id.id, self.team_id.manager_id.user_id.name)
    #
    #     self.message_post(message, subtype='mail.mt_note')

    def send_request(self):
        self.state = 'send'

        # self.add_followers()
        # self.send_message()


    def approve_this(self):

        self.state = 'approved'

    def start_working(self):

        if not self.description_ids:
            raise exceptions.UserError(_('You Has Not Description Of Maintenance'))

        check_desc = self.description_ids.search([('specialist_id', '=', False), ('workorder_id', '=', self.id)])

        if check_desc:
            raise exceptions.UserError(_('This Work Order In Task Has Not Specialist'))

        day = datetime.today()

        self.start_date = day.strftime('%Y-%m-%d')

        date_planned = day + timedelta(hours=self.planned_end_hours)

        self.planned_end_date = date_planned.strftime('%Y-%m-%d')

        self.state = 'started'

    def end_working(self):
        day = datetime.today()

        self.end_date = day.strftime('%Y-%m-%d')

        if self.end_date > self.planned_end_date:
            self.time_effectiveness = 'mild'
            self.effectiveness = 25
        elif self.end_date < self.planned_end_date:
            self.time_effectiveness = 'optimum'
            self.effectiveness = 100
        else:
            self.time_effectiveness = 'normal'
            self.effectiveness = 150

        self.state = 'ended'

    def cancel_work(self):
        self.state = 'cancel'

        for d in self.description_ids:
            d.cancel_work()

    @api.model
    def create(self, values):
        # Add code here
        ID = super(WorkOrder, self).create(values)

        sequence = self.env['ir.sequence'].next_by_code(
            'workorder.maintenance.cp')
        ID.name = sequence

        ID.team_id = ID.equipment_id.team_id
        # self.add_specialist(ID)

        return ID

    # def add_specialist(self, ID):
    #
    #     ID.specialist_id = ID.equipment_id.team_id.members_ids[0]

class PlannedParts(models.Model):
    _name = 'maintenance.cp.planned.parts'
    _description = 'Planned Parts'

    name = fields.Char(string="Description", required=True, )
    workorder_id = fields.Many2one(comodel_name="maintenance.cp.workorder",
                                   string="Work Order", required=False, )
    product_id = fields.Many2one(comodel_name="product.product", string="Product",
                                 required=True, domain="[('is_part', '=', 'True')]")
    product_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'),
                               required=True)
    state = fields.Selection(string="State",
                             selection=[('stock', 'On Stock'),
                                        ('unavailable', 'Unavailable'),
                                        ('available', 'Available'),
                                        ],
                             required=False, )
    vendor_id = fields.Many2one(comodel_name="res.partner", string="Suggested Vendor", required=True,
                                domain=[('supplier', '=', True)])
    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)
    task_id = fields.Many2one(comodel_name="maintenance.cp.task", string="Task", required=False, )

class Service(models.Model):
    _name = 'maintenance.cp.service'
    _rec_name = 'name'
    _description = 'Service Maintenance'

    name = fields.Char(string="Description", required=True, )
    workorder_id = fields.Many2one(comodel_name="maintenance.cp.workorder", string="Work Order", required=False, )
    product_id = fields.Many2one(comodel_name="product.product", string="Service",
                                 required=True, domain="[('is_workforce', '=', 'True')]")
    estimated_cost = fields.Float(string='Estimated Cost', required=True,
                                  digits=dp.get_precision('Product Price'))
    vendor_id = fields.Many2one(comodel_name="res.partner", string="Suggested Vendor", required=True, domain=[('supplier', '=', True)])
    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)

class DescriptionMaintenance(models.Model):
    _name = 'maintenance.cp.description.task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _description = 'Description Task Maintenance'

    sequence = fields.Integer(string="Sequence", required=False, )

    name = fields.Char(string="Name", required=False, related='task_id.name', store=True)
    description = fields.Char(string="Description", required=False, )

    type_workforce_id = fields.Many2one(comodel_name="maintenance.cp.type.workforce",
                                        string="Type of Workforce", required=True, store=True)
    state = fields.Selection(string="Status",
                             selection=[
                                        ('prepared', 'Prepared'),
                                        ('started', 'Started'),
                                        ('ended', 'Ended'),
                                        ('cancel', 'Cancel'),
                                        ],
                             required=False, default="prepared")
    task_id = fields.Many2one(comodel_name="maintenance.cp.task", string="Task", required=True,
                              domain="[('type_workforce_id', '=', type_workforce_id)]", store=True)

    workorder_id = fields.Many2one(comodel_name="maintenance.cp.workorder", string="Work Order", required=False, store=True)

    start_date = fields.Datetime(string="Start Date", required=False, )
    end_date = fields.Datetime(string="End Date", required=False, )
    planned_end_date = fields.Datetime(string="Planned End Date", required=False, )
    planned_end_hours = fields.Float(string="Planned End Hours", required=False, )
    end_hours = fields.Float(string="End Hours", required=False, )

    time_effectiveness = fields.Selection(string="Time Effectiveness", selection=[('mild', 'Mild'), ('normal', 'Normal'), ('optimum', 'Optimum'),
                                                   ], required=False, )
    effectiveness = fields.Integer(string="Effectiveness %", required=False, )

    team_id = fields.Many2one(comodel_name="maintenance.cp.team",
                              string="Equipment Team", required=False, store=True)
    specialist_id = fields.Many2one(comodel_name="hr.employee", string="Specialist",
                                    required=False, domain="[('type_workforce_id', '=', type_workforce_id)]", store=True)
    user_id = fields.Many2one(comodel_name="res.users", string="User", required=False, )

    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)
    workforce_cost = fields.Float(string="Workforce Cost",  required=False, compute='', store=True)
    workforce_cost_total = fields.Float(string="Workforce Cost Total",  required=False,
                                        compute='_compute_workforce_cost_total', store=True)
    equipment_id = fields.Many2one(comodel_name="maintenance.cp.equipment", string="Equipment",
                                   store=True, related="workorder_id.equipment_id")
    category_id = fields.Many2one(comodel_name="maintenance.cp.equipment.category",
                                  string="Category", related="workorder_id.category_id", )
    location_id = fields.Many2one(comodel_name="maintenance.cp.equipment.location",
                                  string="Location", related="workorder_id.location_id", )
    end_hours_by_specialist = fields.Float(string="End Hours", required=False, )
    end_hours_by_supervisor = fields.Float(string="End Hours", required=False, )
    is_checked = fields.Boolean(string="Checked By Supervisor", )

    @api.multi
    def check_task(self):
        self.is_checked = True


    @api.onchange('task_id')
    def _onchange_task_id(self):
        for record in self:
            record.planned_end_hours = self.task_id.planned_end_hours

    @api.one
    @api.depends('specialist_id')
    def _compute_workforce_cost(self):
        """
        @api.depends() should contain all fields that will be used in the calculations.
        """
        contract = self.specialist_id.contract_id

        horas = 30 * 60
        self.workforce_cost = contract.wage/horas

    @api.one
    @api.depends('workforce_cost', 'end_hours')
    def _compute_workforce_cost_total(self):
        """
        @api.depends() should contain all fields that will be used in the calculations.
        """
        self.workforce_cost_total = self.workforce_cost * self.end_hours

    @api.model
    def create(self, values):
        # Add code here
        ID = super(DescriptionMaintenance, self).create(values)

        # ID.add_followers()

        ID.planned_end_hours = ID.task_id.planned_end_hours

        if ID.specialist_id:

            ID.user_id = ID.specialist_id.user_id
            ID.team_id = ID.specialist_id.team_id

        return ID

    @api.onchange('specialist_id')
    def _onchange_specialist_id(self):
        self.user_id = self.specialist_id.user_id
        self.team_id = self.specialist_id.team_id

    def start_working(self):

        if not self.specialist_id:
            raise exceptions.UserError(_('This Task Has Not Specialist'))

        day = datetime.today()

        self.start_date = day.strftime('%Y-%m-%d')

        date_planned = day + timedelta(hours=self.planned_end_hours)

        self.planned_end_date = date_planned.strftime('%Y-%m-%d')

        self.state = 'started'

        self.workorder_id.start_working()

        message = '''<div class="res.users">The specialist <a href="#" class="o_redirect" data-oe-id="%s">@%s</a> start this task <a href="#" class="o_redirect" data-oe-id="%s">@%s</a> and <a href="#" class="o_redirect" data-oe-id="%s">@%s</a></div>''' \
                  % (
                  self.specialist_id.user_id.id, self.specialist_id.user_id.name, self.team_id.supervisor_id.user_id.id,
                  self.team_id.supervisor_id.user_id.name, self.team_id.manager_id.user_id.id,
                  self.team_id.manager_id.user_id.name)

        self.workorder_id.message_post(message, subtype='mail.mt_note')

        self.message_post(message, subtype='mail.mt_note')

    def end_working(self):
        day = datetime.today()

        self.end_date = day.strftime('%Y-%m-%d')

        if self.end_date > self.planned_end_date:
            self.time_effectiveness = 'mild'
            self.effectiveness = 25
        elif self.end_date < self.planned_end_date:
            self.time_effectiveness = 'optimum'
            self.effectiveness = 150
        else:
            self.time_effectiveness = 'normal'
            self.effectiveness = 100

        task = self.workorder_id.description_ids.filtered(lambda r: r.state == 'prepared' or r.state == 'started')

        start_date = datetime.strptime(self.start_date, '%Y-%m-%d %H:%S:%M')

        date_total = relativedelta(start_date, day)

        total_hours = date_total.hours

        self.end_hours = total_hours

        if not task:
            self.workorder_id.end_working()

        self.state = 'ended'

        message = '''<div class="res.users">The specialist <a href="#" class="o_redirect" data-oe-id="%s">@%s</a> end this task <a href="#" class="o_redirect" data-oe-id="%s">@%s</a> and <a href="#" class="o_redirect" data-oe-id="%s">@%s</a></div>''' \
                  % (
                      self.specialist_id.user_id.id, self.specialist_id.user_id.name,
                      self.team_id.supervisor_id.user_id.id,
                      self.team_id.supervisor_id.user_id.name, self.team_id.manager_id.user_id.id,
                      self.team_id.manager_id.user_id.name)

        self.workorder_id.message_post(message, subtype='mail.mt_note')

        self.message_post(message, subtype='mail.mt_note')


    def cancel_work(self):
        self.state = 'cancel'

    def add_followers(self):

        list_followers = [self.team_id.supervisor_id.id, self.team_id.manager_id.id]

        self.message_subscribe_users(list_followers)


    def view_operations(self):

        return {
            'name': ('Task'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'maintenance.cp.task',
            'target': 'new',
            'res_id': self.task_id.id,
            'context': self.env.context,
        }

