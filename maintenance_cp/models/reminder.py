from odoo import fields, models, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import exceptions

class ReminderTask(models.Model):
    _name = 'maintenance.reminder.task'
    _description = 'Reminder Task'
    _rec_name = 'name'

    name = fields.Char(
        string='Name',
        required=True)
    reminder_for = fields.Selection(
        string='Reminder For',
        selection=[('start', 'Start Task'),
                   ('end', 'End Task'), ],
        required=True, default='start')
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='User Reminder',
        required=False, default=lambda self: self.env.user)
    technician_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Technician',
        required=False)
    category_id = fields.Many2one(
        comodel_name='maintenance.cp.equipment.category',
        string='Category',
        required=False)
    location_id = fields.Many2one(
        comodel_name='maintenance.cp.equipment.location',
        string='Location',
        required=False)
    equipment_id = fields.Many2one(
        comodel_name="maintenance.cp.equipment",
        string="Equipment",
        required=False)
    reminder_by = fields.Selection(
        string='Reminder By',
        selection=[('task', 'Task'),
                   ('tech', 'Technician'),
                   ('category', 'Category'),
                   ('location', 'Location'),
                   ('equipment', 'Equipment'),
                   ],
        required=True, )
    execute_every = fields.Integer(
        string='Execute Every',
        required=True, default=1)
    execute_type = fields.Selection(
        string='Execute Type',
        selection=[('minutes', 'Minutes'),
                   ('hours', 'Hours'),
                   ('days', 'Days'),
                   ('weeks', 'Weeks'),
                   ('months', 'Months'),
                   ],
        required=True, default='months')
    nextcall = fields.Datetime(
        string='Next Call',
        required=True)

    @api.multi
    def execute_notification(self):
        today = datetime.now()

        # raise exceptions.UserError((today))
        if self.reminder_by == 'task':
            self.execute_by_task(self)
        if self.reminder_by == 'tech':
            self.execute_by_technician(self)
        if self.reminder_by == 'category':
            self.execute_by_category(self)
        if self.reminder_by == 'location':
            self.execute_by_location(self)
        if self.reminder_by == 'equipment':
            self.execute_by_equipment(self)

        # execute_type ('minutes', 'Minutes'),
        #                ('hours', 'Hours'),
        #                ('days', 'Days'),
        #                ('weeks', 'Weeks'),
        #                ('months', 'Months'),
        #                ],

        if self.execute_type == 'minutes':
            # next_date = datetime.strptime(reminder.nexcall, "%Y-%m-%d %H:%M:%S")
            to_date = today + relativedelta(minutes=self.execute_every)
            self.nextcall = fields.Datetime.to_string(to_date)

        if self.execute_type == 'hours':
            # next_date = datetime.strptime(reminder.nexcall, "%Y-%m-%d %H:%M:%S")
            to_date = today + relativedelta(hours=self.execute_every)
            self.nextcall = fields.Datetime.to_string(to_date)

        if self.execute_type == 'days':
            # next_date = datetime.strptime(reminder.nexcall, "%Y-%m-%d %H:%M:%S")
            to_date = today +  relativedelta(days=self.execute_every)
            self.nextcall = fields.Datetime.to_string(to_date)

        if self.execute_type == 'weeks':
            # next_date = datetime.strptime(reminder.nexcall, "%Y-%m-%d %H:%M:%S")
            to_date = today + relativedelta(weeks=self.execute_every)
            self.nextcall = fields.Datetime.to_string(to_date)

        if self.execute_type == 'months':
            # next_date = datetime.strptime(reminder.nexcall, "%Y-%m-%d %H:%M:%S")
            to_date = today + relativedelta(months=self.execute_every)
            self.nextcall = fields.Datetime.to_string(to_date)

    @api.model
    def execute_by_task(self, reminder):
        task_ids = []
        if reminder.reminder_for == 'start':
            task_ids = self.env['maintenance.cp.description.task'].search(
                [
                    ('reminder_start_id', '=', reminder.id),
                    ('state', '=', 'prepared')
                ]
            )
        elif reminder.reminder_for == 'end':
            task_ids = self.env['maintenance.cp.description.task'].search(
                [
                    ('reminder_end_id', '=', reminder.id),
                    ('state', '=', 'started')
                ]
            )

        self.execute_reminder(task_ids)

    @api.model
    def execute_by_technician(self, reminder):
        task_ids = []
        if reminder.reminder_for == 'start':
            task_ids = self.env['maintenance.cp.description.task'].search(
                [
                    ('reminder_start_id', '=', reminder.id),
                    ('state', '=', 'prepared')
                ]
            )
        elif reminder.reminder_for == 'end':
            task_ids = self.env['maintenance.cp.description.task'].search(
                [
                    ('reminder_end_id', '=', reminder.id),
                    ('state', '=', 'started')
                ]
            )

        self.execute_reminder(task_ids)


    @api.model
    def execute_by_equipment(self, reminder):
        task_ids = []
        if reminder.reminder_for == 'start':
            task_ids = self.env['maintenance.cp.description.task'].search(
                [
                    ('equipment_id', '=', reminder.equipment_id.id),
                    ('state', '=', 'prepared')
                ]
            )
        elif reminder.reminder_for == 'end':
            task_ids = self.env['maintenance.cp.description.task'].search(
                [
                    ('equipment_id', '=', reminder.equipment_id.id),
                    ('state', '=', 'started')
                ]
            )

        self.execute_reminder(task_ids)

    @api.model
    def execute_by_category(self, reminder):

        task_ids = []
        if reminder.reminder_for == 'start':
            task_ids = self.env['maintenance.cp.description.task'].search(
                [
                    ('category_id', '=', reminder.category_id.id),
                    ('state', '=', 'prepared')
                ]
            )
        elif reminder.reminder_for == 'end':
            task_ids = self.env['maintenance.cp.description.task'].search(
                [
                    ('category_id', '=', reminder.category_id.id),
                    ('state', '=', 'started')
                ]
            )

        self.execute_reminder(task_ids)

    @api.model
    def execute_by_location(self, reminder):
        task_ids = []
        if reminder.reminder_for == 'start':
            task_ids = self.env['maintenance.cp.description.task'].search(
                [
                    ('location_id', '=', reminder.location_id.id),
                    ('state', '=', 'prepared')
                ]
            )
        elif reminder.reminder_for == 'end':
            task_ids = self.env['maintenance.cp.description.task'].search(
                [
                    ('location_id', '=', reminder.location_id.id),
                    ('state', '=', 'started')
                ]
            )

        self.execute_reminder(task_ids)

    @api.model
    def execute_reminder(self, task_ids):
        message = ''''''

        message_post_with_view('purchase.track_po_line_template',
                               values={'line': line, 'product_qty': values['product_qty']},
                               subtype_id=self.env.ref('mail.mt_note').id)

        for task in task_ids:
            if task.state == 'prepared':
                message = '''<div class="res.users"><a href="#" class="o_redirect" data-oe-id="%s">@%s</a> 
                you have this task pending for start to work order %s</div>''' \
                          % (task.specialist_id.user_id.id, task.specialist_id.user_id.name, task.workorder_id.name)

                task.message_post_with_view('mail.message_user_assigned',
                                            composition_mode='mass_mail',
                                            partner_ids=[(4, task.specialist_id.user_id.partner_id.id)],
                                            auto_delete=True,
                                            auto_delete_message=True,
                                            parent_id=False,  # override accidental context defaults
                                            subtype_id=self.env.ref('mail.mt_note').id)
            elif task.state == 'started':
                message = '''<div class="res.users"><a href="#" class="o_redirect" data-oe-id="%s">@%s</a> 
                                you have this task pending for end to work order %s</div>''' \
                          % (task.specialist_id.user_id.id, task.specialist_id.user_id.name, task.workorder_id.name)

            # task.message_post(message, subtype='mail.mt_note')

