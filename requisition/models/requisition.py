# -*- coding: utf-8 -*-

from odoo import models, fields, api, _ 
from datetime import timedelta


class Requisition(models.Model):
    _name = 'requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin', 'pad.common']

    name = fields.Char(index=True, track_visibility = 'onchange', help="Nombre de la requisición")
    requisition_type_id = fields.Many2one('budget.requisition',  string='Tipo de Requisición', domain="[('company_id','=',company_id)]")
    company_id = fields.Many2one('res.company',  string='Compañía', store=True, readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('account.bank.statement'))
    date_requisition = fields.Datetime(string='Fecha de Requisición', readonly=True, index=True, default=fields.Datetime.now)
    requisition_line_ids = fields.One2many('requisition.lines', 'requisition_id')
    active = fields.Boolean(default=True, help="Establezca activo en falso para ocultar el registro sin eliminarlo.", track_visibility = 'onchange')
    state = fields.Selection([('draft', 'Borrador'), 
                                ('confirmed', 'Confirmado'),
                                ('approved', 'Aprobado'),
                                ('canceled', 'Anulado')], 
                                string='Estado', required=True, readonly=True, default='draft')
    budget = fields.Float('Cupo', track_visibility = 'onchange', compute='_get_budget')
    total_requisition = fields.Float('Total de Requisición', track_visibility = 'onchange', compute="_amount_total_requisition")

    @api.multi
    def toggle_active(self):
        for record in self:
            record.active = not record.active
    
    @api.depends('requisition_type_id')
    def _get_budget(self):
        for record in self:
            record.budget = record.requisition_type_id.budget
    
    def confirm(self):
        for record in self:
            record.state = 'confirmed'

    def give_back(self):
        for record in self:
            record.state = 'draft'

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('requisition')
        result = super(Requisition, self).create(vals)
        return result

    @api.depends('requisition_line_ids')
    def _amount_total_requisition(self):
        for record in self:
            total = 0.0
            for line in record.requisition_line_ids:
                total += line.sub_total
            record.update({
                'total_requisition': total,
            })


class RequisitionLines(models.Model):
    _name = 'requisition.lines'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin', 'pad.common']

    requisition_id = fields.Many2one('requisition')
    product_id = fields.Many2one('product.product', string='Product', ondelete='restrict', index=True)
    name = fields.Char(track_visibility = 'onchange', string="Descripcipción")
    quantity = fields.Integer(string='Cantidad', help="Ingrese la cantidad de producto a solicitar", track_visibility = 'onchange')
    approved_quantity = fields.Integer(string="Cantidad Aprobada", track_visibility = 'onchange')
    company_id = fields.Many2one('res.company', related='requisition_id.company_id', string='Company', store=True, readonly=True)
    unit_cost = fields.Float('Costo', track_visibility = 'onchange')
    seller_id = fields.Char(string='Proveedor')
    unit_measurement = fields.Char(string= 'Unidad de Medida')
    sub_total = fields.Float('Subtotal', track_visibility = 'onchange', compute="_calculate_subtotal")
    state = fields.Selection(related='requisition_id.state')

    @api.onchange('product_id')
    def info_products(self):
        if self.product_id:
            for record in self:
                record.name = record.product_id.name
                record.unit_cost = record.product_id.standard_price

    @api.onchange('quantity')
    def quantity_approve(self):
        for record in self:
            if record.quantity and record.state == 'draft':
                record.approved_quantity = record.quantity

    @api.depends('approved_quantity')
    def _calculate_subtotal(self):
        for record in self:
            record.sub_total = record.unit_cost * record.approved_quantity
