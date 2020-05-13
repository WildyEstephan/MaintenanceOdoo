# -*- encoding: utf-8 -*-
{
    'name': 'Requisiciones',
    'version': '1.0',
    'depends': ['product', 'purchase', 'mail','portal','pad'],
    'data': [

        'data/data_sequence.xml',
        
        'views/menu_views.xml',
        'views/requisition_config_views.xml',
        'views/requisition_views.xml',
        
        #'views/purchase_order_view_inherit.xml',
    ],
 
    'installable': True,
    'application': True,
}
