# -*- coding: utf-8 -*-
from odoo import http

# class TxtPopularPayslip(http.Controller):
#     @http.route('/txt_popular_payslip/txt_popular_payslip/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/txt_popular_payslip/txt_popular_payslip/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('txt_popular_payslip.listing', {
#             'root': '/txt_popular_payslip/txt_popular_payslip',
#             'objects': http.request.env['txt_popular_payslip.txt_popular_payslip'].search([]),
#         })

#     @http.route('/txt_popular_payslip/txt_popular_payslip/objects/<model("txt_popular_payslip.txt_popular_payslip"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('txt_popular_payslip.object', {
#             'object': obj
#         })