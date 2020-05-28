odoo.define("custom_gantt_view.gantt_view", function(require){
    "use_strict";

    var core = require('web.core');
    var BasicView = require('web.BasicView');
    var ViewRegistry = require('web.view_registry');
    var GanttController = require('custom_gantt_view.GanttController');
    var GanttRenderer = require('custom_gantt_view.GanttRenderer');

    var _t = core._t;
    var _lt = core._lt;

    var GanttCustom = BasicView.extend({
        display_name: _lt('Gantt'),
        icon: 'fas fa-align-left',
        cssLibs: [
            '/custom_gantt_view/static/src/lib/gantt-master/dist/frappe-gantt.css',
            '/custom_gantt_view/static/src/css/style.css'
        ],
        jsLibs: [
            '/custom_gantt_view/static/src/lib/gantt-master/dist/frappe-gantt.min.js'
        ],
        config: _.extend({}, BasicView.prototype.config, {
            Renderer: GanttRenderer,
            Controller: GanttController
        }),
        viewType: 'gantt_custom',
        init: function (viewInfo, params) {
            this._super.apply(this, arguments);
        }
    });

    ViewRegistry.add('gantt_custom', GanttCustom);
    return GanttCustom;

});
