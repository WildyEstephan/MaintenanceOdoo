# -*- coding: utf-8 -*-
from odoo import http

# class RequisitionStockIntegration(http.Controller):
#     @http.route('/requisition_stock_integration/requisition_stock_integration/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/requisition_stock_integration/requisition_stock_integration/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('requisition_stock_integration.listing', {
#             'root': '/requisition_stock_integration/requisition_stock_integration',
#             'objects': http.request.env['requisition_stock_integration.requisition_stock_integration'].search([]),
#         })

#     @http.route('/requisition_stock_integration/requisition_stock_integration/objects/<model("requisition_stock_integration.requisition_stock_integration"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('requisition_stock_integration.object', {
#             'object': obj
#         })