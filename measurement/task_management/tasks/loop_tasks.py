# -*- coding: utf-8 -*-
"""
"""
from traits.api\
    import (Str, Instance, Bool)
from traitsui.api\
     import (View, ListInstanceEditor, VGroup, UItem,
             InstanceEditor, Group, Label, LineCompleterEditor)

from numpy import linspace
from timeit import default_timer

from .tools.task_decorator import make_stoppable
from .tools.database_string_formatter import format_and_eval_string
from .base_tasks import (SimpleTask, ComplexTask)

class BaseLoopTask(ComplexTask):
    """
    """
    task_start = Str('0.0', preference = True)
    task_stop = Str('0.0', preference = True)
    task_step = Str('0.1', preference = True)
    timing = Bool(False)

    task_database_entries = ['point_number']

    def check(self, *args, **kwargs):
        """
        """
        test = True
        traceback = {}
        try:
            start = format_and_eval_string(self.task_start, self.task_path,
                                         self.task_database)
        except:
            test = False
            traceback[self.task_path + '/' + self.task_name] = \
                'Loop task did not success to compute  the start value'
        try:
            stop = format_and_eval_string(self.task_stop, self.task_path,
                                         self.task_database)
        except:
            test = False
            traceback[self.task_path + '/' + self.task_name] = \
                'Loop task did not success to compute  the stop value'
        try:
            step = format_and_eval_string(self.task_step, self.task_path,
                                         self.task_database)
        except:
            test = False
            traceback[self.task_path + '/' + self.task_name] = \
                'Loop task did not success to compute  the step value'
        try:
            num = int(abs((stop - start)/step))+ 1
            self.write_in_database('point_number', num)
        except:
            test = False
            traceback[self.task_path + '/' + self.task_name] = \
                'Loop task did not success to compute point number'
        check = super(LoopTask, self).check( *args, **kwargs)
        test = test and check[0]
        traceback.update(check[1])
        return test, traceback

    def _timing_changed(self, new):
        """
        """
        if new:
            self.process = self.process_with_timing
            self.task_database_entries.append('elapsed_time')
        else:
            self.process = self.process_no_timing
            self.task_database_entries.remove('elapsed_time')

class SimpleLoopTask(BaseLoopTask):
    """Complex task which, at each iteration, call all its child tasks.
    """
    task_database_entries = ['point_number', 'index']

    @make_stoppable
    def process_no_timing(self):
        """
        """
        start = format_and_eval_string(self.task_start, self.task_path,
                                         self.task_database)
        stop = format_and_eval_string(self.task_stop, self.task_path,
                                         self.task_database)
        step = format_and_eval_string(self.task_step, self.task_path,
                                         self.task_database)
        num = int(abs(((stop - start)/step))) + 1
        self.write_in_database('point_number', num)
        for value in linspace(self.task_start, self.task_stop, num):
            self.write_in_database('index', value)
            for child in self.children_task:
                child.process()

    @make_stoppable
    def process_with_timing(self):
        """
        """
        start = format_and_eval_string(self.task_start, self.task_path,
                                         self.task_database)
        stop = format_and_eval_string(self.task_stop, self.task_path,
                                         self.task_database)
        step = format_and_eval_string(self.task_step, self.task_path,
                                         self.task_database)
        num = int(abs(((stop - start)/step))) + 1
        self.write_in_database('point_number', num)
        for value in linspace(self.task_start, self.task_stop, num):
            tic = default_timer()
            for child in self.children_task:
                child.process()
            self.write_in_database('elapsed_time', default_timer()-tic)

    def _list_database_entries(self):
        """
        """
        entries =  self.task_database.list_accessible_entries(self.task_path)
        return entries

    def _define_task_view(self):
        """
     start = format_and_eval_string(self.task_start, self.task_path,
                                         self.task_database)
        stop = format_and_eval_string(self.task_stop, self.task_path,
                                         self.task_database)
        step = format_and_eval_string(self.task_step, self.task_path,
                                         self.task_database)
        num = int(abs(((stop - start)/step))) + 1   """
        line_completer = LineCompleterEditor(
                             entries_updater = self._list_database_entries)

        task_view = View(
                    UItem('task_name', style = 'readonly'),
                    VGroup(
                        VGroup(
                            Group(
                                Label('Start'), Label('Stop'), Label('Step'),
                                Label('Timing'),
                                UItem('task_start', editor = line_completer),
                                UItem('task_stop', editor = line_completer),
                                UItem('task_step', editor = line_completer),
                                UItem('timing'),
                                columns = 4,
                                ),
                            show_border = True,
                            ),
                        UItem('children_task',
                          editor = ListInstanceEditor(
                              style = 'custom',
                              editor = InstanceEditor(view = 'task_view'),
                              item_factory = self.create_child)),
                        show_border = True,
                        ),
                    title = 'Edit task',
                    resizable = True,
                    )
        self.trait_view('task_view', task_view)

class LoopTask(BaseLoopTask):
    """Complex task which, at each iteration, performs a task with a different
    value and then call all its child tasks.
    """
    task = Instance(SimpleTask, child = True)
    task_database_entries = ['point_number']

    @make_stoppable
    def process_no_timing(self):
        """
        """
        start = format_and_eval_string(self.task_start, self.task_path,
                                         self.task_database)
        stop = format_and_eval_string(self.task_stop, self.task_path,
                                         self.task_database)
        step = format_and_eval_string(self.task_step, self.task_path,
                                         self.task_database)
        num = int(abs(((stop - start)/step))) + 1
        self.write_in_database('point_number', num)
        for value in linspace(self.task_start, self.task_stop, num):
            self.task.process(value)
            for child in self.children_task:
                child.process()

    @make_stoppable
    def process_with_timing(self):
        """
        """
        start = format_and_eval_string(self.task_start, self.task_path,
                                         self.task_database)
        stop = format_and_eval_string(self.task_stop, self.task_path,
                                         self.task_database)
        step = format_and_eval_string(self.task_step, self.task_path,
                                         self.task_database)
        num = int(abs(((stop - start)/step))) + 1
        self.write_in_database('point_number', num)
        for value in linspace(self.task_start, self.task_stop, num):
            tic = default_timer()
            for child in self.children_task:
                child.process()
            self.write_in_database('elapsed_time', default_timer()-tic)

    def _list_database_entries(self):
        """
        """
        entries =  self.task_database.list_accessible_entries(self.task_path)
        return entries

    def _define_task_view(self):
        line_completer = LineCompleterEditor(
                             entries_updater = self._list_database_entries)

        task_view = View(
                    UItem('task_name', style = 'readonly'),
                    VGroup(
                        VGroup(
                            Group(
                                Label('Start'), Label('Stop'), Label('Step'),
                                Label('Timing'),
                                UItem('task_start', editor = line_completer),
                                UItem('task_stop', editor = line_completer),
                                UItem('task_step', editor = line_completer),
                                UItem('timing'),
                                columns = 4,
                                ),
                            UItem('task', style = 'custom',
                                  editor = InstanceEditor(view = 'loop_view')),
                            show_border = True,
                            ),
                        UItem('children_task',
                          editor = ListInstanceEditor(
                              style = 'custom',
                              editor = InstanceEditor(view = 'task_view'),
                              item_factory = self.create_child)),
                        show_border = True,
                        ),
                    title = 'Edit task',
                    resizable = True,
                    )
        self.trait_view('task_view', task_view)