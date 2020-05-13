# -*- coding: utf-8 -*-

from odoo import models, fields, api, _ 

class RequisitionPeriods(models.Model):
    _name = 'period.requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin', 'pad.common']

    name = fields.Char(index=True, track_visibility = 'onchange', help="Ingrese el nombre del periodo")
    time_days = fields.Integer(string='Tiempo en Días', help="Ingrese el tiempo de espera para autorización automática", track_visibility = 'onchange')
    active = fields.Boolean(default=True, help="Establezca activo en falso para ocultar el registro sin eliminarlo.")

    @api.multi
    def toggle_active(self):
        for record in self:
            record.active = not record.active


class RequisitionTypes(models.Model):
    _name = 'types.requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin', 'pad.common']

    name = fields.Char(index=True, track_visibility = 'onchange', help="Ingrese el nombre del periodo")
    active = fields.Boolean(default=True, help="Establezca activo en falso para ocultar el registro sin eliminarlo.")
    period_requisition_id = fields.Many2one('period.requisition', string='Periodo')
    company_ids = fields.Many2many('res.company', 'res_company_requisition_rel', 'req_type_id', 'company_id',
        string='Compañías')

    @api.multi
    def toggle_active(self):
        for record in self:
            record.active = not record.active
    
    @api.one
    @api.constrains('company_ids')
    def create_budget(self):
        vals = {
            'name': self.name,
            'types_requisition_id': self.id,
            }
        for company in self.company_ids:
            if not self.exists_budget(self.id, company.id):
                self._create_budget(vals, company.id)
        self.unlink_budget()

    
    def exists_budget(self, type_req, company):
        exists = False
        budget = self.env['budget.requisition'].search([('types_requisition_id','=',type_req),('company_id','=',company)])
        if budget:
            exists = True
        return exists
    
    def _create_budget(self, vals, company):
        bud = self.env['budget.requisition']
        budget = bud.create({
                            'name': vals['name'],
                            'types_requisition_id': vals['types_requisition_id'],
                            'budget':0.0,
                            'company_id': company
                            })
    
    def unlink_budget(self):
        companys = list(self.mapped('company_ids.id'))
        budget = self.env['budget.requisition'].search([('types_requisition_id','=',self.id)])
        for company in budget:
            if company.company_id.id not in companys:
                company.active = False


            
class RequisitionBudget(models.Model):
    _name = 'budget.requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin', 'pad.common']

    name = fields.Char(index=True, track_visibility = 'onchange')
    active = fields.Boolean(default=True, help="Establezca activo en falso para ocultar el registro sin eliminarlo.")
    types_requisition_id = fields.Many2one('types.requisition', string='Tipo de Requisición')
    budget = fields.Float('Presupuesto', track_visibility = 'onchange')
    company_id = fields.Many2one('res.company',  string='Compañía', store=True, readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('account.bank.statement'))

    @api.multi
    def toggle_active(self):
        for record in self:
            record.active = not record.active
