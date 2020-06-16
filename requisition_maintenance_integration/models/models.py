# -*- coding: utf-8 -*-


from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError, AccessError
from odoo.tools.misc import formatLang
from odoo.addons.base.res.res_partner import WARNING_MESSAGE, WARNING_HELP
from odoo.addons import decimal_precision as dp

class WorkOrder(models.Model):
    _inherit = 'maintenance.cp.workorder'

    picking_ids = fields.One2many(comodel_name="stock.picking", inverse_name="workorder_id", string="Receptions", required=False, )
    # picking_count = fields.Integer(string="Receptions Count", compute='_compute_picking_count', )

    requisition_ids = fields.One2many(comodel_name="requisition", inverse_name="workorder_id",
                                    string="Requisitions", required=False, )

    # requisition_count = fields.Integer(string="Requisition Count", compute='_compute_requisition_count', )

    # @api.one
    # @api.depends('picking_count')
    # def _compute_picking_count(self):
    #     """
    #     @api.depends() should contain all fields that will be used in the calculations.
    #     """
    #     self.picking_count = len(self.picking_ids)
    #
    # @api.one
    # @api.depends('requisition_count')
    # def _compute_picking_count(self):
    #     """
    #     @api.depends() should contain all fields that will be used in the calculations.
    #     """
    #     self.requisition_count = len(self.requisition_ids)

    @api.multi
    def approve_this(self):

        self.state ='approved'

        if self.is_checked:
            pass
        else:
            self.check_task_parts()

        self.parts_ids.sudo().check_qty_available()

        self.sudo().create_picking()
        self.sudo().create_requisition_by_parts()
        # self.sudo().create_requisition_by_service()

    @api.multi
    def create_picking(self):
        copy_record = self.env['stock.picking']
        qty = 0.0

        for record in self:
            order_lines = []
            for rec in record.parts_ids:
                qty = 0.0
                if not rec.product_id.type == 'service':

                    if not rec.product_id.qty_available == 0 or not rec.product_id.qty_available < 0:

                        if rec.qty_remaining <= 0:
                            qty = rec.product_qty
                        else:
                            continue
                            # qty = rec.product_id.qty_available

                        if rec.state == 'stock':
                            order_lines.append(
                                (0, 0,
                                 {
                                     'product_id': rec.product_id.id,
                                     'product_uom_qty': qty,
                                     'name': record.name,
                                     'product_uom': rec.product_id.uom_id.id,
                                     'planned_parts_id': rec.id,
                                 }
                                 ))

            if order_lines:
                sp_types = self.env['stock.picking.type'].search([
                    ('code', '=', 'internal')
                ])[0]

                location_dest = self.env.ref('requisition_maintenance_integration.stock_location_maintenance_cp')

                copy_record.create({
                        'origin': record.name,
                        'picking_type_id': sp_types.id,
                        'location_id': sp_types.default_location_src_id.id,
                        'location_dest_id': location_dest.id,
                        'move_lines': order_lines,
                        'move_type': 'direct',
                        'priority': '1',
                        'company_id': record.company_id.id,
                        'workorder_id': record.id
                    })

    @api.multi
    def create_requisition_by_parts(self):

        copy_record = self.env['requisition']
        for record in self:
            order_lines = []
            for rec in record.parts_ids:

                if (rec.qty_remaining > 0) or (rec.product_id.type == 'service'):
                    order_lines.append(
                        (0, 0,
                         {
                             'product_id': rec.product_id.id,
                             'quantity': rec.qty_remaining or 1,
                             'name': record.name,
                             'unit_measurement': rec.product_id.uom_id.id,
                             'planned_parts_id': rec.id,
                             'seller_id': rec.vendor_id.id
                         }
                         ))

            if order_lines:

                copy_record.create({
                    'name': record.name + ' Purchase Maintenance Service',
                    'requisition_line_ids': order_lines,
                    'company_id': record.company_id.id,
                    'workorder_id': record.id
                })

    @api.multi
    def create_requisition_by_service(self):

        copy_record = self.env['requisition']
        for record in self:
            order_lines = []
            for rec in record.service_ids:
                order_lines.append(
                    (0, 0,
                     {
                         'product_id': rec.product_id.id,
                         'quantity': 1,
                         'name': record.name,
                         'unit_measurement': rec.product_id.uom_id.id,
                         'workorder_service_id': rec.id,
                         'unit_cost': rec.estimated_cost,
                         'seller_id': rec.vendor_id.id
                     }
                     ))

            if order_lines:
                sp_types = self.env['stock.picking.type'].search([
                    ('code', '=', 'internal')
                ])[0]

                location_dest = self.env.ref('requisition_maintenance_integration.stock_location_maintenance_cp')

                copy_record.create({
                    'name': record.name + ' Purchase Maintenance Consumable',
                    'requisition_line_ids': order_lines,
                    'company_id': record.company_id.id,
                    'workorder_id': record.id
                })

class PlannedParts(models.Model):
    _inherit = 'maintenance.cp.planned.parts'

    # qty_available = fields.Float(
    #     'Quantity On Hand',
    #     digits=dp.get_precision('Product Unit of Measure'), )

    qty_remaining = fields.Float(
        'Remaining quantity',
        digits=dp.get_precision('Product Unit of Measure'), )

    move_ids = fields.One2many('stock.move', 'planned_part_id', string='Reservation', readonly=True,
                               ondelete='set null', copy=False)

    @api.multi
    def check_qty_available(self):

        for record in self:

            if not record.product_id.type == 'service':
                record.state = 'stock'
                record.qty_remaining = record.product_qty - record.product_id.qty_available

class Requisition(models.Model):
    _inherit = 'requisition'

    workorder_id = fields.Many2one(comodel_name="maintenance.cp.workorder", string="Work Order", required=False, )


class RequisitionLines(models.Model):
    _inherit = 'requisition.lines'

    planned_parts_id = fields.Many2one(comodel_name="maintenance.cp.planned.parts",
                                       string="Part Line", required=False, )

    workorder_service_id = fields.Many2one(comodel_name="maintenance.cp.service",
                                       string="Service Line", required=False, )


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    _order = 'name desc'

    workorder_id = fields.Many2one(comodel_name="maintenance.cp.workorder", string="Work Order", required=False, )

class StockMove(models.Model):
    _inherit = 'stock.move'

    planned_part_id = fields.Many2one(comodel_name="maintenance.cp.planned.parts",
                                   string="Planned Part", required=False, )
