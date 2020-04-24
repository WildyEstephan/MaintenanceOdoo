from odoo import api, fields, models
from odoo.addons import decimal_precision as dp
from datetime import datetime, timedelta

class WorkOrder(models.Model):
    _name = 'maintenance.cp.workorder'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _description = 'Equipment Work Order'

    name = fields.Char(string="Sequence", required=False, )
    equipment_id = fields.Many2one(comodel_name="maintenance.cp.equipment", string="Equipment",
                                   required=True, )
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
    planned_end_hours = fields.Float(string="Planned End Hours", required=False, )
    end_hours = fields.Float(string="End Hours",  required=False, )

    # El encargado de la orden de trabajo
    # Este campo sera llenado con el tecnico que tenga menos horas planeadas en sus ordenes de trabajo.
    # Si existe mas de un tecnico que cumple con la primera condicion se elige quien tenga mayor efectividad
    # de entrega a tiempo
    specialist_id = fields.Many2one(comodel_name="hr.employee", string="Specialist", required=False, )

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

    def add_followers(self):

        list_followers = [self.specialist_id.id, self.team_id.supervisor_id.id, self.team_id.manager_id.id]

        self.message_subscribe_users(list_followers)

    def send_message(self):
        message = '''<div class="res.users"><a href="#" class="o_redirect" data-oe-id="%s">@%s</a>, <a href="#" class="o_redirect" data-oe-id="%s">@%s</a> and <a href="#" class="o_redirect" data-oe-id="%s">@%s</a>, you have a new request</div>''' \
                  % (self.specialist_id.user_id.id, self.specialist_id.user_id.name,self.team_id.supervisor_id.user_id.id, self.team_id.supervisor_id.user_id.name, self.team_id.manager_id.user_id.id, self.team_id.manager_id.user_id.name)

        self.message_post(message, subtype='mail.mt_note')

    def send_request(self):
        self.state = 'send'

        self.add_followers()
        self.send_message()


    def approve_this(self):

        self.state = 'approved'

    def start_working(self):

        day = datetime.today()

        self.start_date = day.strftime('%Y-%m-%d')

        date_planned = day + timedelta(hours=self.planned_end_hours)

        self.planned_end_date = date_planned.strftime('%Y-%m-%d')

        self.state = 'started'

    def end_working(self):
        day = datetime.today()

        self.end_date = day.strftime('%Y-%m-%d')

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
    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)

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

    name = fields.Char(string="Name", required=False, related='task_id.name')
    description = fields.Char(string="Description", required=False, )

    type_workforce_id = fields.Many2one(comodel_name="maintenance.cp.type.workforce",
                                        string="Type of Workforce", required=True, )
    state = fields.Selection(string="Status",
                             selection=[
                                        ('prepared', 'Prepared'),
                                        ('started', 'Started'),
                                        ('ended', 'Ended'),
                                        ('cancel', 'Cancel'),
                                        ],
                             required=False, default="prepared")
    task_id = fields.Many2one(comodel_name="maintenance.cp.task", string="Task", required=True,
                              domain="[('type_workforce_id', '=', type_workforce_id)]")

    workorder_id = fields.Many2one(comodel_name="maintenance.cp.workorder", string="Work Order", required=False, )

    start_date = fields.Datetime(string="Start Date", required=False, )
    end_date = fields.Datetime(string="End Date", required=False, )
    planned_end_date = fields.Datetime(string="Planned End Date", required=False, )
    planned_end_hours = fields.Float(string="Planned End Hours", required=False, )
    end_hours = fields.Float(string="End Hours", required=False, )

    team_id = fields.Many2one(comodel_name="maintenance.cp.team",
                              string="Equipment Team", required=False, )
    specialist_id = fields.Many2one(comodel_name="hr.employee", string="Specialist",
                                    required=True, domain="[('type_workforce_id', '=', type_workforce_id)]")
    user_id = fields.Many2one(comodel_name="res.users", string="User", required=False,)

    company_id = fields.Many2one(comodel_name="res.company",
                                 string="Company",
                                 required=False,
                                 default=lambda self: self.env.user.company_id.id)

    @api.model
    def create(self, values):
        # Add code here
        ID = super(DescriptionMaintenance, self).create(values)

        ID.add_followers()

        ID.user_id = ID.specialist_id.user_id
        ID.team_id = ID.specialist_id.team_id

        return ID

    @api.onchange('specialist_id')
    def _onchange_specialist_id(self):
        self.user_id = self.specialist_id.user_id
        self.team_id = self.specialist_id.team_id

    def start_working(self):

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

