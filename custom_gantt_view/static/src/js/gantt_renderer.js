odoo.define('custom_gantt_view.GanttRenderer', function (require) {
"use strict";

var BasicRenderer = require('web.BasicRenderer');
var AbstractRenderer = require('web.AbstractRenderer');
var config = require('web.config');
var core = require('web.core');
var dom = require('web.dom');
var rpc = require('web.rpc');

var GlobalTaskArray = {};

function dateParser (mydate) {
    if (mydate !== undefined) {
        var date_time = mydate.split(" ");
        var date = date_time[0].split("-");
        try{
            var time = date_time[1].split(":");
        }
        catch (err){
            var time = [23,59,0];
        }

        var finalDate = new Date(date[0], date[1]-1, date[2], time[0],time[1]);
        var finalDate = finalDate.getTime();
        return finalDate;
    }
}

var GanttRenderer = BasicRenderer.extend({
    className: "o_gantt_view",
    id: "o_gantt_view_id",
    events: _.extend({}, AbstractRenderer.prototype.events, {
        'mouseover .rect_text': 'ShowTag',
        'mouseout .rect_text': 'HideTag'
    }),
    HideTag: function(event){
        setTimeout(function(){
            var output = document.getElementById("tag");
            output.style.visibility = "hidden";
        }, 200);
    },
    ShowTag: function(event){
        setTimeout(function(){
            var x = event.clientX;
            var y = event.clientY;

            var task_id = $(event.currentTarget).attr("task_id");

            var current_task = GlobalTaskArray[task_id];
            if(!current_task){
                return false;
            }
            var tag = "Task: " + current_task.task + "<br/>" +
                        "Group: " + current_task.type + "<br/>" +
                        "Starts: " + current_task.startdate + "<br/>" +
                        "Ends: " + current_task.enddate + "<br/>" ;
            var output = document.getElementById("tag");

            output.innerHTML = tag;
            output.style.top = y + 'px';
            output.style.left = x + 'px';
            output.style.visibility = "visible";
            output.style.display = "inline-block";
            output.style.position = "fixed";
        }, 500);
    },
    /**
     * @override
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.result = {};
    },
    _collect_field_attributes: function(){
        var attrs = this.arch.attrs;
        var result = {
            label: attrs.string ? attrs.string : "Gantt View",
            model: this.state.model,
            date_start: attrs.start_date ? attrs.start_date: null,
            date_end: attrs.end_date ? attrs.end_date : null,
            col: attrs.group_by ? attrs.group_by : null
        };
        if(!result['date_start'] || !result['date_end']
            || !result['col'] || !result['model']){
            alert("Incorrect view configuration !")
        }
        this.result = result;
        return ;
    },
	create_source: function(tasks){
		if(!tasks){
			return [];
		}
		var task;
		var sources = [];

		/*for(var i in tasks) {
			tasks[i].color = ['#'+ ('000000' + Math.floor(Math.random()*16777215).toString(16)).slice(-6),
                '#'+ ('000000' + Math.floor(Math.random()*16777215).toString(16)).slice(-6)];
		}*/
        var progress, current_time, total_time, worked_time;
        current_time = dateParser(tasks[1]);
        for(var i in tasks[0]){
            total_time = 0, worked_time = 0;
            for (var j=0; j<tasks[0][i].length; j++){
                task = tasks[0][i][j];
                if(task.parent == true){
                    total_time += (dateParser(task.end) - dateParser(task.start));
                }
                else if (current_time >= dateParser(task.start)){
                    worked_time += (current_time - dateParser(task.start))
                }
            }
			for (var j=0; j<tasks[0][i].length; j++){
				task = tasks[0][i][j];

                if(task.parent == true) {
                    progress = (worked_time / total_time) * 100;
                    task.progress = progress;
                    task.custom_class = 'bar_parent';
                }

				sources.push(task);
			}
		}

		return sources;
	},
    _renderView: function () {
        // render the form and evaluate the modifiers
        var defs = [];
        this.defs = defs;
        delete this.defs;
        this._collect_field_attributes();
        var self = this;
		var data = this.state.data;
        this.view_mode = 'Day';
		var required_input = [];
		for (var index=0;index<data.length;index++){
			required_input.push(data[index].res_id);
		}

        return $.when.apply($, defs).then(function () {
             rpc.query({
                 model: 'custom.gantt.content',
                 method: 'fetch_gantt_contents',
                 args: [self.result, required_input]
             }).then(function (tasks) {
				 self.taskArray = tasks;
                 self.renderGantt(tasks);
             });
        });
     },
    update_time: function (task, start, end) {
        try{
            var parent = this.taskArray[0][task.type_id];
            var p_time, p_time_end, c_time_start, c_time_end, s_time_start, s_time_end;
            var new_s_date;
            p_time = dateParser(parent[0].start);
            p_time_end = dateParser(parent[0].end);
            s_time_start = dateParser(start);
            s_time_end = dateParser(end);
            for(var i in parent){
                if(parent[i]['id'] == task.id){
                    /*changing date of selected bar*/
                    var old_start = dateParser(parent[i].start);
                    var old_end = dateParser(parent[i].end);
                    parent[i].start = start;
                    parent[i].end = end;
                    c_time_start = dateParser(parent[i].start);
                    c_time_end = dateParser(parent[i].end);
                    new_s_date = parent[i].start;
                    /*updating date of parent*/
                    if(p_time == s_time_start){}
                    else if(p_time > s_time_start){
                        parent[0].start = start;
                    }
                    else if(p_time == old_start){
                        /*checking old start date and selecting new one
                        * this child was the the earliest task*/
                        for(var p in parent){
                            if(parent[p].parent == false){
                                if(dateParser(parent[p].start) < c_time_start){
                                    new_s_date = parent[p].start;
                                }
                            }
                        }
                        parent[0].start = new_s_date;
                    }

                    if(p_time_end == s_time_end){}
                    else if(s_time_end > p_time_end){
                        parent[0].end = end;
                    }
                    else if(old_end == p_time_end){
                        /*checking old end date and selecting new one
                        * this child was the the final task*/
                        new_s_date = parent[i].end;
                        for(var p in parent){
                            if(parent[p].parent == false){
                                if(c_time_end < dateParser(parent[p].end)){
                                    new_s_date = parent[p].end;
                                }
                            }
                        }
                        parent[0].end = new_s_date;
                    }
                }
            }
        }
        catch (err){}
    },
    renderGantt: function(taskArray){
        var self = this;
		var sources = this.create_source(taskArray);
        $("#gantt_custom").remove();
        var gantt_div = '<div id="gantt_custom" class="gantt_custom">' +
            '<div class="btn-group mt-3 mx-auto gantt-controll-buttons" role="group">' +
            '<button type="button" class="btn btn-sm btn-light quarter_day">Quarter Day</button>' +
            '<button type="button" class="btn btn-sm btn-light half_day">Half Day</button>' +
            '<button type="button" class="btn btn-sm btn-light full_day">Day</button>' +
            '<button type="button" class="btn btn-sm btn-light week">Week</button>' +
            '<button type="button" class="btn btn-sm btn-light month">Month</button>' +
            '<button type="button" class="btn btn-sm btn-light reload_gantt_button" title="Reload Gantt">' +
            '<i class="fa fa-refresh" ></i></button>' +
            '</div></div>';

        var active_mode, old_mode;
        switch (this.view_mode){
            case 'Quarter Day': old_mode = 'quarter_day'; active_mode = 'quarter_day active'; break;
            case 'Half Day': old_mode = 'half_day'; active_mode = 'half_day active'; break;
            case 'Day': old_mode = 'full_day'; active_mode = 'full_day active'; break;
            case 'Week': old_mode = 'week'; active_mode = 'week active'; break;
            case 'Month': old_mode = 'month'; active_mode = 'month active'; break;
            default: old_mode = 'full_day'; active_mode = 'full_day active';
        };
        gantt_div = gantt_div.replace(old_mode, active_mode);

        var $gantt_div = $(gantt_div);

        if (sources.length === 0) {
            sources = [{
                name: 'No records to display!'
            }];
        }
        var html_string = $gantt_div[0].outerHTML;
        $(html_string).prependTo(self.$el);
        var gantt = new Gantt("#gantt_custom", sources, {
            header_height: 50,
            column_width: 30,
            step: 24,
            view_modes: ['Quarter Day', 'Half Day', 'Day', 'Week', 'Month'],
            bar_height: 20,
            bar_corner_radius: 3,
            arrow_curve: 5,
            padding: 18,
            view_mode: self.view_mode ? self.view_mode:'Day',
            date_format: 'YYYY-MM-DD',
            custom_popup_html: null,
            on_click: function (task) {
                console.log(task);
            },
            on_date_change: function(task, start, end) {
                if(task.child=true){
                    /*task*/
                    var d = new Date(start);
                    var start_date = d.getUTCFullYear() + "-" +
                        (d.getUTCMonth() + 1) + "-" + d.getUTCDate() + " " +
                        d.getUTCHours() + ":" + d.getUTCMinutes();
                    d = new Date(end);
                    var end_date = d.getUTCFullYear() + "-" +
                        (d.getUTCMonth() + 1) + "-" + d.getUTCDate() + " " +
                        d.getUTCHours() + ":" + d.getUTCMinutes();
                    self.update_time(task, start_date, end_date);
                    rpc.query({
                        model: 'custom.gantt.content',
                        method: 'update_time_range',
                        args: [
                            task,
                            self.result,
                            start_date,
                            end_date
                        ]
                    });
                }
                else if(task.parent == true){
                    /*type*/
                }
            },
            on_progress_change: function(task, progress) {
                console.log("on_progress_change", task, progress);
            }
        });
        $('.quarter_day').click(function(evt){
            $('.btn-light').removeClass('active');
            $(this).addClass('active');
            self.view_mode = 'Quarter Day';
            gantt.change_view_mode('Quarter Day');
        });
        $('.half_day').click(function(evt){
            $('.btn-light').removeClass('active');
            $(this).addClass('active');
            self.view_mode = 'Half Day';
            gantt.change_view_mode('Half Day');
        });
        $('.full_day').click(function(evt){
            $('.btn-light').removeClass('active');
            $(this).addClass('active');
            self.view_mode = 'Day';
            gantt.change_view_mode('Day');
        });
        $('.week').click(function(evt){
            $('.btn-light').removeClass('active');
            $(this).addClass('active');
            self.view_mode = 'Week';
            gantt.change_view_mode('Week');
        });
        $('.month').click(function(evt){
            $('.btn-light').removeClass('active');
            $(this).addClass('active');
            self.view_mode = 'Month';
            gantt.change_view_mode('Month');
        });
        $('.reload_gantt_button').click(function(evt){
            self.renderGantt(self.taskArray);
        });
    }
});

return GanttRenderer;
});
