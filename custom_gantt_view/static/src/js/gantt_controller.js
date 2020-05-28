odoo.define('custom_gantt_view.GanttController', function (require) {
"use strict";

var BasicController = require('web.BasicController');


var GanttController = BasicController.extend({
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
    },
    renderPager: function ($node, options) {
        return false;
    },
});

return GanttController;

});
