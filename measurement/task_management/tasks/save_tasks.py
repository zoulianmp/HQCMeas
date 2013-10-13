# -*- coding: utf-8 -*-
"""
"""

from traits.api import (Instance, Array, List, Str, Enum, Any, HasTraits,
                        Button, Bool, Int, on_trait_change)
from traitsui.api import (View, HGroup, VGroup, UItem, ObjectColumn, Handler,
                          TableEditor, Label, LineCompleterEditor, Group)
from pyface.qt import QtGui

import os, numpy
from inspect import cleandoc

from .tools.database_string_formatter import (get_formatted_string,
                                              format_and_eval_string)
from .tools.task_decorator import make_stoppable, make_wait
from .base_tasks import SimpleTask

class SavedValueObject(HasTraits):
    """
    """

    label = Str
    value = Str

class HeaderHandler(Handler):
    """
    """
    def object_def_header_changed(self, info):
        """
        """
        model = info.object
        database = model.task_database
        entries = database.list_accessible_entries(model.task_path)
        if 'default_header' in entries:
            model.header = model.get_from_database('default_header')
        else:
            model.header = ''

class SaveTaskHandler(Handler):
    """
    """
    def object_explore_button_changed(self, info):
        """
        """
        dlg = QtGui.QFileDialog(info.ui.control)
        dlg.setFileMode(QtGui.QFileDialog.Directory)
        if dlg.exec_() == QtGui.QDialog.Accepted:
            directory = dlg.selectedFiles()[0]
            info.object.folder = directory

    def object_fill_header_changed(self, info):
        """
        """
        task = info.object
        task.edit_traits(view = 'header_view',
                                parent = info.ui.control,
                                kind = 'livemodal')

class SaveTask(SimpleTask):
    """
    """
    folder = Str('', preference = True)
    filename = Str('', preference = True)
    file_object = Any
    header = Str('', preference = True)
    def_header = Button('Default header')
    fill_header = Button('Edit')

    array = Array

    saving_target = Enum('File', 'Array', 'File and array', preference = True)

    array_size = Str(preference = True)
    array_length = Int
    line_index = Int(0)

    saved_labels = List(Str, preference = True)
    saved_values = List(Str, preference = True)
    saved_objects = List(Instance(SavedValueObject))

    initialized = Bool(False)
    task_database_entries = {'file' : None}
    explore_button = Button('Browse')

    #task_view = View()
    header_view = View(
                    UItem('header@'),
                    UItem('def_header'),
                    handler = HeaderHandler(),
                    buttons = ['OK', 'Cancel'])

    def __init__(self, *args, **kwargs):
        super(SaveTask, self).__init__(*args, **kwargs)
        self._define_task_view()
        self.on_trait_change(name = 'saved_objects:[label, value]',
                             handler = self._saved_objects_modified)

    @make_stoppable
    @make_wait()
    def process(self):
        """
        """
        #Init
        if not self.initialized:
            if self.saving_target != 'Array':
                full_folder_path = get_formatted_string(self.folder,
                                                         self.task_path,
                                                         self.task_database)
                filename = get_formatted_string(self.filename, self.task_path,
                                                         self.task_database)
                full_path = os.path.join(full_folder_path, filename)
                try:
                    self.file_object = open(full_path, 'w')
                except IOError:
                    print 'In {}, failed to open the specified file'.format(
                                                                self.task_name)
                    self.root_task.should_stop.set()
                    return

                self.write_in_database('file', self.file_object)
                if self.header:
                    for line in self.header.split('\n'):
                        self.file_object.write('# ' + line + '\n')
                self.file_object.write('\t'.join(self.saved_labels) + '\n')
                self.file_object.flush()

            if self.saving_target != 'File':
                self.array_length = format_and_eval_string(self.array_size,
                                                           self.task_path,
                                                           self.task_database)
                print [(name, 'f8') for name in self.saved_labels]
                array_type = numpy.dtype([(str(name), 'f8')
                                            for name in self.saved_labels])
                self.array = numpy.empty((self.array_length),
                                         dtype = array_type)
                self.write_in_database('array', self.array)
            self.initialized = True

        #writing
        values = [format_and_eval_string(value,
                                       self.task_path,
                                       self.task_database)
                    for value in self.saved_values]
        if self.saving_target != 'Array':
            self.file_object.write('\t'.join([str(val)
                                              for val in values]) + '\n')
            self.file_object.flush()
        if self.saving_target != 'File':
            self.array[self.line_index] = tuple(values)

        self.line_index += 1

        #Closing
        if self.line_index == self.array_length:
            self.write_in_database('array', self.array)
            self.file_object.close()
            self.initialized = False

    def check(self, *args, **kwargs):
        """
        """
        traceback = {}
        try:
            full_folder_path = get_formatted_string(self.folder,
                                                         self.task_path,
                                                         self.task_database)
        except:
            traceback[self.task_path + '/' +self.task_name] = \
                'Failed to format the folder path'
            return False, traceback

        try:
            filename = get_formatted_string(self.filename, self.task_path,
                                                         self.task_database)
        except:
            traceback[self.task_path + '/' +self.task_name] = \
                'Failed to format the filename'
            return False, traceback

        full_path = os.path.join(full_folder_path, filename)

        try:
            f = open(full_path, 'wb')
            f.close()
        except:
            traceback[self.task_path + '/' +self.task_name] = \
                'Failed to open the specified file'
            return False, traceback

        try:
            format_and_eval_string(self.array_size,
                                       self.task_path,
                                       self.task_database)
        except:
            traceback[self.task_path + '/' +self.task_name] = \
                'Failed to compute the array size'
            return False, traceback

        test = True
        for i, value in enumerate(self.saved_values):
            try:
                format_and_eval_string(value,
                                   self.task_path,
                                   self.task_database)
            except:
                traceback[self.task_path + '/' +self.task_name + str(i)] = \
                    'Failed to evaluate entry : {}'.format(self.saved_labels[i])
                test = False

        if self.saving_target != 'File':
            data = [numpy.array([0.0,1.0]) for lab in self.saved_labels]
            names = str(','.join(self.saved_labels))
            final_arr = numpy.rec.fromarrays(data, names = names)

        self.write_in_database('array', final_arr)

        return test, traceback

    def update_preferences_from_traits(self):
        """
        """
        self._saved_objects_modified()
        for name in self.traits(preference = True):
            self.task_preferences[name] = str(self.get(name).values()[0])

    def update_traits_from_preferences(self, **parameters):
        """
        """
        super(SaveTask, self).update_traits_from_preferences(**parameters)
        self.on_trait_change(name = 'saved_objects:[label, value]',
                             handler = self._saved_objects_modified,
                             remove = True)
        for i, label in enumerate(self.saved_labels):
            self.saved_objects.append(
                    SavedValueObject(label = label,
                                     value = self.saved_values[i]))
        self.on_trait_change(name = 'saved_objects:[label, value]',
                             handler = self._saved_objects_modified)

    def _saved_objects_modified(self):
        """
        """
        self.saved_labels = [obj.label for obj in self.saved_objects]
        self.saved_values = [obj.value for obj in self.saved_objects]

    def _list_database_entries(self):
        """
        """
        entries =  self.task_database.list_accessible_entries(self.task_path)
        return entries

    @on_trait_change('saving_target')
    def _update_database_entries(self, new):
        """
        """
        if new == 'File':
            self.task_database_entries = {'file' : None}
        elif new == 'Array':
            self.task_database_entries = {'array' : numpy.array([1.0])}
        else:
            self.task_database_entries = {'file' : None,
                                          'array' : numpy.array([1.0])}
    def _define_task_view(self):
        """
        """
        line_completer = LineCompleterEditor(
                             entries_updater = self._list_database_entries)
        label_col = ObjectColumn(name = 'label',
                         label = 'Label',
                         horizontal_alignment = 'center',
                         width = 0.4,
                         )
        value_col = ObjectColumn(name = 'value',
                         label = 'Value',
                         horizontal_alignment = 'center',
                         editor = line_completer,
                         width = 0.6,
                         )
        table_editor = TableEditor(
                editable  = True,
                sortable  = False,
                auto_size = False,
                reorderable = True,
                deletable = True,
                row_factory = SavedValueObject,
                columns = [label_col,
                            value_col],
                )
        view = View(
                UItem('task_name', style = 'readonly'),
                VGroup(
                    HGroup(
                        Label('Save to :'),
                        UItem('saving_target'),
                        ),
                    HGroup(
                        Label('# of points'),
                        UItem('array_size',
                            editor = line_completer,
                            tooltip = "Enter the number of points to be saved",
                            springy = True,
                            ),
                        ),
                    HGroup(
                        HGroup(
                            UItem('folder',
                                editor = line_completer,
                                springy = True,
                                ),
                            UItem('explore_button'),
                            label = 'Folder',
                            show_border = True,
                            ),
                        HGroup(
                            UItem('filename',editor = line_completer,
                                  springy = True),
                            label = 'Filename',
                            show_border = True,
                            ),
                        HGroup(
                            UItem('fill_header'),
                            label = 'Header',
                            show_border = True,
                            ),
                    enabled_when = "saving_target != 'Array'"
                    ),
                    UItem('saved_objects',
                        editor = table_editor,
                        ),
                    show_border = True,
                    ),
                handler = SaveTaskHandler(),
                resizable = True,
                )
        self.trait_view('task_view', view)


class SaveArrayTask(SimpleTask):
    """
    """
    folder = Str('', preference = True)
    explore_button = Button('Browse')
    filename = Str('', preference = True)
    file_object = Any
    header = Str('', preference = True)
    def_header = Button('Default header')
    fill_header = Button('Edit')

    target_array = Str(preference = True)
    mode = Enum('Text file', 'Binary file', preference = True)

    #task_view = View()
    header_view = View(
                    UItem('header@'),
                    UItem('def_header'),
                    handler = HeaderHandler(),
                    buttons = ['OK', 'Cancel'])

    def __init__(self, *args, **kwargs):
        super(SaveArrayTask, self).__init__(*args, **kwargs)
        self._define_task_view()

    @make_stoppable
    @make_wait()
    def process(self):
        """
        """
        array_to_save = self.get_from_database(self.target_array[1:-1])

        full_folder_path = get_formatted_string(self.folder,
                                                         self.task_path,
                                                         self.task_database)
        filename = get_formatted_string(self.filename, self.task_path,
                                                 self.task_database)
        full_path = os.path.join(full_folder_path, filename)

        if self.mode == 'Text file':
            try:
                self.file_object = open(full_path, 'wb')
            except IOError:
                print 'In {}, failed to open the specified file'.format(
                                                            self.task_name)
                self.root_task.should_stop.set()
                return

            if self.header:
                for line in self.header.split('\n'):
                    self.file_object.write('# ' + line + '\n')
            if array_to_save.dtype.names:
                self.file_object.write('\t'.join(array_to_save.dtype.names) + \
                                        '\n')
            numpy.savetxt(self.file_object, array_to_save, delimiter = '\t')
            self.file_object.close()

        else:
            try:
                self.file_object = open(full_path, 'wb')
                self.file_object.close()
            except IOError:
                print 'In {}, failed to open the specified file'.format(
                                                            self.task_name)
                self.root_task.should_stop.set()
                return

            numpy.save(full_path, array_to_save)

    def check(self, *args, **kwargs):
        """
        """
        traceback = {}
        try:
            full_folder_path = get_formatted_string(self.folder,
                                                         self.task_path,
                                                         self.task_database)
        except:
            traceback[self.task_path + '/' +self.task_name] = \
                'Failed to format the folder path'
            return False, traceback

        if self.mode == 'Binary file':
            if len(self.filename) > 3:
                if self.filename[-4] == '.' and self.filename[-3:] != 'npy':
                    self.filename = self.filename[:-4] + '.npy'
                    print cleandoc("""The extension of the file will be replaced
                        by '.npy' in task {}""".format(self.task_name))

        try:
            filename = get_formatted_string(self.filename, self.task_path,
                                                         self.task_database)
        except:
            traceback[self.task_path + '/' +self.task_name] = \
                'Failed to format the filename'
            return False, traceback

        full_path = os.path.join(full_folder_path, filename)

        try:
            f = open(full_path, 'wb')
            f.close()
        except:
            traceback[self.task_path + '/' +self.task_name] = \
                'Failed to open the specified file'
            return False, traceback

        entries = self.task_database.list_accessible_entries(self.task_path)
        if self.target_array[1:-1] not in entries:
            traceback[self.task_path + '/' +self.task_name] = \
                'Specified array is absent from the database'
            return False, traceback

        return True, traceback

    def _list_database_entries(self):
        """
        """
        entries =  self.task_database.list_accessible_entries(self.task_path)
        return entries

    def _define_task_view(self):
        """
        """
        line_completer = LineCompleterEditor(
                             entries_updater = self._list_database_entries)
        view = View(
                UItem('task_name', style = 'readonly'),
                VGroup(
                    HGroup(
                        UItem('folder',
                            editor = line_completer,
                            springy = True,
                            ),
                        UItem('explore_button'),
                        label = 'Folder',
                        show_border = True,
                        ),
                    HGroup(
                        HGroup(
                            UItem('filename', editor = line_completer,
                                  springy = True),
                            label = 'Filename',
                            show_border = True,
                            ),
                        HGroup(
                            UItem('fill_header'),
                            label = 'Header',
                            show_border = True,
                            ),
                            ),
                    Group(
                        Label('Mode'),Label('Array to save'),
                        UItem('mode'),
                        UItem('target_array', editor = line_completer),
                        columns = 2,
                        ),
                    show_border = True,
                    ),
                handler = SaveTaskHandler(),
                resizable = True,
                )
        self.trait_view('task_view', view)