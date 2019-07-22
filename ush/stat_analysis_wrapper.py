#!/usr/bin/env python

'''
Program Name: stat_analysis_wrapper.py
Contact(s): Mallory Row
Abstract: Runs stat_analysis
History Log: Fourth version
Usage: stat_analysis_wrapper.py
Parameters: None
Input Files: MET STAT files
Output Files: MET STAT files
Condition codes: 0 for success, 1 for failure
'''

from __future__ import (print_function, division)

import logging
import os
import sys
import copy
import met_util as util
import re
import csv
import subprocess
import datetime
import time
import calendar
import itertools
import string_template_substitution as sts
from command_builder import CommandBuilder


class StatAnalysisWrapper(CommandBuilder):
    """! Wrapper to the MET tool stat_analysis which is used to filter 
         and summarize data from MET's point_stat, grid_stat, 
         ensemble_stat, and wavelet_stat
    """
    def __init__(self, config, logger):
        super(StatAnalysisWrapper, self).__init__(config, logger)
        self.app_path = os.path.join(self.config.getdir('MET_INSTALL_DIR'),
                                     'bin/stat_analysis')
        self.app_name = os.path.basename(self.app_path)
        
        self.c_dict = self.create_c_dict()     

    def set_lookin_dir(self, lookindir):
        self.lookindir = "-lookin "+lookindir+" "
   
    def get_command(self):
        if self.app_path is None:
            self.logger.error(self.app_name + ": No app path specified. \
                              You must use a subclass")
            return None

        cmd = self.app_path + " "
        for a in self.args:
            cmd += a + " "

        if self.lookindir == "":
            self.logger.error(self.app_name+": No lookin directory specified")
            return None
        
        cmd += self.lookindir
         
        if self.param != "":
            cmd += "-config " + self.param + " "
        return cmd
     
    def create_c_dict(self):
        """! Create a data structure (dictionary) that contains all the
             values set in the configuration files that are common for 
             stat_analysis_wrapper.py.
        
             Args:
 
             Returns:
                 c_dict  - a dictionary containing the settings in the
                           configuration files unique to the wrapper
        """
        c_dict = dict()
        c_dict['LOOP_ORDER'] = self.config.getstr('config', 'LOOP_ORDER')
        c_dict['PROCESS_LIST'] = self.config.getstr('config', 'PROCESS_LIST')
        c_dict['CONFIG_FILE'] = self.config.getstr('config', 
                                                   'STAT_ANALYSIS_CONFIG_FILE')
        c_dict['OUTPUT_BASE_DIR'] = self.config.getdir('STAT_ANALYSIS_OUTPUT_DIR')
        c_dict['GROUP_LIST_ITEMS'] = util.getlist(
            self.config.getstr('config', 'GROUP_LIST_ITEMS')
            )
        c_dict['LOOP_LIST_ITEMS'] = util.getlist(
            self.config.getstr('config', 'LOOP_LIST_ITEMS')
            )
        c_dict['MODEL_LIST'] = util.getlist(
            self.config.getstr('config', 'MODEL_LIST', '')
            )
        c_dict['DESC_LIST'] = util.getlist(
            self.config.getstr('config', 'DESC_LIST', '')
            )
        c_dict['FCST_LEAD_LIST'] = util.getlist(
            self.config.getstr('config', 'FCST_LEAD_LIST', '')
            )
        c_dict['OBS_LEAD_LIST'] = util.getlist(
            self.config.getstr('config', 'OBS_LEAD_LIST', '')
            )
        c_dict['FCST_VALID_HOUR_LIST'] = util.getlist(
            self.config.getstr('config', 'FCST_VALID_HOUR_LIST', '')
            )
        c_dict['FCST_INIT_HOUR_LIST'] = util.getlist(
            self.config.getstr('config', 'FCST_INIT_HOUR_LIST', '')
            )
        c_dict['OBS_VALID_HOUR_LIST'] = util.getlist(
            self.config.getstr('config', 'OBS_VALID_HOUR_LIST', '')
            )
        c_dict['OBS_INIT_HOUR_LIST'] = util.getlist(
            self.config.getstr('config', 'OBS_INIT_HOUR_LIST', '')
            )
        c_dict['VX_MASK_LIST'] = util.getlist(
            self.config.getstr('config', 'VX_MASK_LIST', '')
            )
        c_dict['INTERP_MTHD_LIST'] = util.getlist(
            self.config.getstr('config', 'INTERP_MTHD_LIST', '')
            )
        c_dict['INTERP_PNTS_LIST'] = util.getlist(
            self.config.getstr('config', 'INTERP_PNTS_LIST', '')
            )
        c_dict['COV_THRESH_LIST'] = util.getlist(
            self.config.getstr('config', 'COV_THRESH_LIST', '')
            )
        c_dict['ALPHA_LIST'] = util.getlist(
            self.config.getstr('config', 'ALPHA_LIST', '')
            )
        c_dict['LINE_TYPE_LIST'] = util.getlist(
            self.config.getstr('config', 'LINE_TYPE_LIST', '')
            )
        return c_dict

    def list_to_str(self, list_of_values):
        """! Turn a list of values into a single string so it can be 
             set to an environment variable and read by the MET 
             stat_analysis config file.
                 
             Args:
                 list_of_values - list of values
  
             Returns:
                 list_as_str    - string created from list_of_values
                                  with the values separated by commas 
        """
        list_as_str=''
        if len(list_of_values) > 0:
            for lt in range(len(list_of_values)):
                if lt == len(list_of_values)-1:
                    list_as_str = list_as_str+'"'+str(list_of_values[lt]+'"')
                else:
                    list_as_str = list_as_str+'"'+str(list_of_values[lt]+'", ')
        return list_as_str
    
    def set_lists_loop_or_group(self, config_lists_to_group_items,
                                config_lists_to_loop_items, config_dict):
        """! Determine whether the lists from the METplus config file
             should treat the items in that list as a group or items 
             to be looped over based on user settings, the values
             in the list, and process being run.
             
             Args:
                 config_lists_to_group_items - list of the METplus 
                                               config list names
                                               to group the list's 
                                               items set by user
                 config_lists_to_loop_items  - list of the METplus 
                                               config list names
                                               to loop over the 
                                               list's items set by 
                                               user
                 config_dict                 - dictionary containing
                                               the configuration 
                                               information
             
             Returns: 
                 lists_to_group_items        - list of all the list names 
                                               whose items are being 
                                               grouped together
                 lists_to_loop_items         - list of all the list names 
                                               whose items are being
                                               looped over 
        """
        expected_config_lists = [
             'MODEL_LIST', 'DESC_LIST',
             'FCST_LEAD_LIST', 'OBS_LEAD_LIST',
             'FCST_VALID_HOUR_LIST', 'FCST_INIT_HOUR_LIST',
             'OBS_VALID_HOUR_LIST', 'OBS_INIT_HOUR_LIST',
             'FCST_VAR_LIST', 'OBS_VAR_LIST',
             'FCST_UNITS_LIST', 'OBS_UNITS_LIST',
             'FCST_LEVEL_LIST', 'OBS_LEVEL_LIST',
             'VX_MASK_LIST', 'INTERP_MTHD_LIST',
             'INTERP_PNTS_LIST', 'FCST_THRESH_LIST',
             'OBS_THRESH_LIST', 'COV_THRESH_LIST',
             'ALPHA_LIST', 'LINE_TYPE_LIST'
             ]
        if (self.c_dict['LOOP_ORDER'] == 'processes' 
                and 'MakePlots' in self.c_dict['PROCESS_LIST']):
            lists_to_group_items = config_lists_to_group_items
            lists_to_loop_items = config_lists_to_loop_items
            for config_list in expected_config_lists:
                if (not config_list in config_lists_to_group_items
                        and not config_list in config_lists_to_loop_items):
                    if config_list == 'LINE_TYPE_LIST':
                        lists_to_group_items.append(config_list)
                    elif config_dict[config_list] == []:
                        self.logger.warning(
                            config_list+" is empty, will be treated as group."
                            )
                        lists_to_group_items.append(config_list)
                    else:
                        lists_to_loop_items.append(config_list)
                elif (config_list in config_lists_to_loop_items
                          and config_dict[config_list] == []):
                    self.logger.warning(
                        config_list+" is empty, will be treated as group."
                        )
                    lists_to_group_items.append(config_list)
                    lists_to_loop_items.remove(config_list)
        else:
            lists_to_group_items = config_lists_to_group_items
            lists_to_loop_items = config_lists_to_loop_items
            for config_list in expected_config_lists:
                if (not config_list in config_lists_to_group_items
                        and not config_list in config_lists_to_loop_items):
                    lists_to_group_items.append(config_list)
                elif (config_list in config_lists_to_loop_items
                          and config_dict[config_list] == []):
                    self.logger.warning(
                        config_list+" is empty, will be treated as group."
                        )
                    lists_to_group_items.append(config_list)
                    lists_to_loop_items.remove(config_list)
        self.logger.debug(
            "Items in these lists will be grouped together: " \
            +', '.join(lists_to_group_items)
            )
        self.logger.debug(
            "Items in these lists will be looped over: " \
            +', '.join(lists_to_loop_items)
            )
        return lists_to_group_items, lists_to_loop_items
  
    def build_stringsub_dict(self, date_beg, date_end, date_type,
                             lists_to_loop, lists_to_group, config_dict):
        """! Build a dictionary with list names, dates, and commonly
             used identifiers to pass to string_template_substitution.
            
             Args:
                 date_beg       - string of the beginning date in
                                  YYYYMMDD form
                 date_end       - string of the end date in YYYYMMDD
                                  form
                 date_type      - string of the date type, either
                                  VALID or INIT
                 lists_to_loop  - list of all the list names whose items
                                  are being grouped together
                 lists_to group - list of all the list names whose items
                                  are being looped over
                 config_dict    - dictionary containing the configuration 
                                  information
            
             Returns:
                 stringsub_dict - dictionary containing the formatted
                                  information to pass to the 
                                  string_template_substitution
        """
        stringsub_dict = {}
        stringsub_dict[date_type.lower()+'_beg'] = datetime.datetime.strptime(
            date_beg, '%Y%m%d'
            )
        stringsub_dict[date_type.lower()+'_end'] = datetime.datetime.strptime(
            date_end, '%Y%m%d'
            )
        if date_beg == date_end:
             stringsub_dict[date_type.lower()] = datetime.datetime.strptime(
                 date_beg, '%Y%m%d'
                 )
        for loop_list in lists_to_loop:
             list_name = loop_list.replace('_LIST', '')
             list_name_value = config_dict[list_name] \
                 .replace('"', '') \
                 .replace(' ', '')
             if 'HOUR' in list_name:
                 stringsub_dict[list_name.lower()] = (
                     datetime.datetime.strptime(list_name_value, '%H%M%S')
                     )
                 stringsub_dict[list_name.lower()+'_beg'] = stringsub_dict[
                     list_name.lower()
                     ]
                 stringsub_dict[list_name.lower()+'_end'] = stringsub_dict[
                     list_name.lower()
                     ]
                 if date_type in list_name:
                     list_type = list_name \
                         .replace('_'+date_type+'_HOUR', '') \
                         .lower()
                     stringsub_dict[list_type+'_'+date_type.lower()+'_beg'] = (
                         datetime.datetime.strptime(date_beg
                                                    +list_name_value, 
                                                    '%Y%m%d%H%M%S')
                         )
                     stringsub_dict[list_type+'_'+date_type.lower()+'_end'] = (
                         datetime.datetime.strptime(date_end
                                                    +list_name_value, 
                                                    '%Y%m%d%H%M%S')
                         )
                     if date_beg == date_end:
                         stringsub_dict[list_type+'_'+date_type.lower()] = (
                             datetime.datetime.strptime(date_beg
                                                        +list_name_value, 
                                                        '%Y%m%d%H%M%S')
                             )
                     check_hour_list = [ 
                         'FCST_'+date_type+'_HOUR_LIST', 
                         'OBS_'+date_type+'_HOUR_LIST' 
                         ]
                     if not all(l in lists_to_loop for l in check_hour_list):
                         stringsub_dict[date_type.lower()+'_hour'] = (
                             stringsub_dict[list_type+'_'
                                            +date_type.lower()+'_hour']
                             )
                         stringsub_dict[date_type.lower()+'_hour_beg'] = (
                             stringsub_dict[list_type+'_'
                                            +date_type.lower()+'_hour']
                             )
                         stringsub_dict[date_type.lower()+'_hour_end'] = (
                             stringsub_dict[list_type+'_'
                                            +date_type.lower()+'_hour']
                             )
                         stringsub_dict[date_type.lower()+'_beg'] = (
                             stringsub_dict[list_type+'_'
                                            +date_type.lower()+'_beg']
                             )
                         stringsub_dict[date_type.lower()+'_end'] = (
                             stringsub_dict[list_type+'_'
                                            +date_type.lower()+'_end']
                             )
                         if date_beg == date_end:
                             stringsub_dict[date_type.lower()] = (
                                 stringsub_dict[list_type+'_'
                                                +date_type.lower()]
                                 )
             elif 'LEAD' in list_name:
                 lead_timedelta = datetime.timedelta(
                     hours=int(list_name_value[0:2]),
                     minutes=int(list_name_value[2:4]),
                     seconds=int(list_name_value[4:])
                     )
                 stringsub_dict[list_name.lower()] = int(
                     lead_timedelta.total_seconds()
                     )
                 list_type = list_name.replace('_LEAD', '').lower()
                 if date_type == 'VALID':
                     stringsub_dict[list_type+'_init_beg'] = (
                         stringsub_dict[list_type+'_valid_beg']
                         - lead_timedelta
                         )
                     stringsub_dict[list_type+'_init_end'] = (
                         stringsub_dict[list_type+'_valid_end']
                         - lead_timedelta
                         )
                     if date_beg == date_end:
                         stringsub_dict[list_type+'_init'] = (
                             stringsub_dict[list_type+'_valid']
                             - lead_timedelta
                         )
                 elif date_type == 'INIT':
                     stringsub_dict[list_type+'_valid_beg'] = (
                         stringsub_dict[list_type+'_init_beg'] 
                         + lead_timedelta
                         )
                     stringsub_dict[list_type+'_valid_end'] = (
                         stringsub_dict[list_type+'_init_end']
                         + lead_timedelta
                         )
                     if date_beg == date_end:
                         stringsub_dict[list_type+'_valid'] = (
                             stringsub_dict[list_type+'_init']
                             + lead_timedelta
                             )
                 check_lead_list = [ 'FCST_LEAD_LIST', 'OBS_LEAD_HOUR_LIST' ]
                 if not all(l in lists_to_loop for l in check_lead_list):
                     stringsub_dict['lead'] = stringsub_dict[list_name.lower()]
                     if date_type == 'VALID':
                         stringsub_dict['init_beg'] = (
                             stringsub_dict[list_type+'_init_beg']
                             )
                         stringsub_dict['init_end'] = (
                             stringsub_dict[list_type+'_init_end']
                             )
                         if date_beg == date_end:
                             stringsub_dict['init'] = (
                                 stringsub_dict[list_type+'_init']
                             )
                     elif date_type == 'INIT':
                         stringsub_dict['valid_beg'] = (
                            stringsub_dict[list_type+'_valid_beg']
                            )
                         stringsub_dict['valid_end'] = (
                            stringsub_dict[list_type+'_valid_end']
                            )
                         if date_beg == date_end:
                             stringsub_dict['valid'] = (
                                 stringsub_dict[list_type+'_valid']
                                 )
             elif list_name == 'MODEL':
                 stringsub_dict[list_name.lower()] = list_name_value
                 stringsub_dict['obtype'] = config_dict['OBTYPE'] \
                     .replace('"', '') \
                     .replace(' ', '')
             else:
                 stringsub_dict[list_name.lower()] = list_name_value
        for group_list in lists_to_group:
            list_name = group_list.replace('_LIST', '')
            list_name_value = config_dict[list_name] \
                .replace('"', '') \
                .replace(' ', '') \
                .replace(',', '')
            check_valid_init_hour_list = [
                'FCST_VALID_HOUR_LIST', 'FCST_INIT_HOUR_LIST',
                'OBS_VALID_HOUR_LIST', 'OBS_INIT_HOUR_LIST'
                ]
            if group_list in check_valid_init_hour_list:
                stringsub_dict[list_name.lower()] = list_name_value
                list_name_values_list = config_dict[list_name] \
                    .replace('"', '') \
                    .split(', ')
                if list_name_values_list != ['']:
                    stringsub_dict[list_name.lower()+'_beg'] = (
                        datetime.datetime.strptime(list_name_values_list[0], 
                                                   '%H%M%S')
                        )
                    stringsub_dict[list_name.lower()+'_end'] = (
                        datetime.datetime.strptime(list_name_values_list[-1], 
                                                   '%H%M%S')
                        )
                else:
                    stringsub_dict[list_name.lower()+'_beg'] = (
                        list_name_values_list[0]
                        )
                    stringsub_dict[list_name.lower()+'_end'] = (
                        list_name_values_list[-1]
                        )
            else:
                stringsub_dict[list_name.lower()] = list_name_value
        hour_type_list = [ 'VALID', 'INIT' ]
        time_type_list = [ 'beg', 'end' ]
        for hour_type in hour_type_list:
            check_hour_type_list = [ 
                'FCST_'+hour_type+'_HOUR_LIST', 'OBS_'+hour_type+'_HOUR_LIST' 
                ]
            if all(l in lists_to_group for l in check_hour_type_list):
                hour_type_low = hour_type.lower()
                for time_type in time_type_list:
                    fcst_hour_time_name = (
                        'fcst_'+hour_type_low+'_hour_'+time_type
                    )
                    obs_hour_time_name = (
                        'obs_'+hour_type_low+'_hour_'+time_type
                    )
                    hour_time_name = hour_type_low+'_hour_'+time_type
                    if (stringsub_dict[fcst_hour_time_name] 
                            == stringsub_dict[obs_hour_time_name]):
                        stringsub_dict[hour_time_name] = (
                           stringsub_dict[fcst_hour_time_name]
                           )
                    elif (stringsub_dict[fcst_hour_time_name] != ''
                              and stringsub_dict[obs_hour_time_name] == ''):
                         stringsub_dict[hour_time_name] = (
                           stringsub_dict[fcst_hour_time_name]
                           )
                    elif (stringsub_dict[fcst_hour_time_name] == ''
                              and stringsub_dict[obs_hour_time_name] != ''):
                         stringsub_dict[hour_time_name] = (
                           stringsub_dict[obs_hour_time_name]
                           )
                    elif (stringsub_dict[fcst_hour_time_name] == ''
                              and stringsub_dict[obs_hour_time_name] == ''):
                         if time_type == 'beg':
                             time_str = '000000'
                         elif time_type == 'end':
                             time_str = '230000'
                         stringsub_dict[hour_time_name] = (
                             datetime.datetime.strptime(time_str, '%H%M%S')
                             )
        return stringsub_dict

    def get_output_filename(self, output_type, filename_template,
                            filename_type, date_beg, date_end, date_type,
                            lists_to_loop, lists_to_group, config_dict):
        """! Create a file name for stat_analysis output.
             
             Args:
                 output_type       - string for the type of
                                     stat_analysis output, either 
                                     dump_row or out_stat
                 filename_template - string of the template to be used 
                                     to create the file name
                 filename_type     - string of the source of the
                                     template being used, either 
                                     default or user
                 date_beg          - string of the beginning date in
                                     YYYYMMDD form
                 date_end          - string of the end date in YYYYMMDD
                                     form
                 date_type         - string of the date type, either
                                     VALID or INIT
                 lists_to_loop     - list of all the list names whose
                                     items are being grouped together
                 lists_to group    - list of all the list names whose
                                     items are being looped over
                 config_dict       - dictionary containing the
                                     configuration information

             Returns:
                 output_filename   - string of the filled file name
                                     template
        """
        if filename_type == 'default':
            if ('MakePlots' in self.c_dict['PROCESS_LIST'] 
                        and output_type == 'dump_row'):
                filename_template = ( 
                    filename_template+'{'+date_type.lower()+'_beg?fmt=%Y%m%d}'
                    +'to{'+date_type.lower()+'_end?fmt=%Y%m%d}_'
                    +'valid{valid_hour_beg?fmt=%H%M%S}to'
                    +'{valid_hour_end?fmt=%H%M%S}Z_'
                    +'init{init_hour_beg?fmt=%H%M%S}to'
                    +'{init_hour_end?fmt=%H%M%S}Z_lead{lead?fmt=%HH%MM%SS}'
                    +'_fcst{fcst_var?fmt=%s}{fcst_level?fmt=%s}'
                    +'{fcst_thresh?fmt=%s}{interp_mthd?fmt=%s}_'
                    +'obs{obs_var?fmt=%s}{obs_level?fmt=%s}'
                    +'{obs_thresh?fmt=%s}{interp_mthd?fmt=%s}_'
                    +'vxmask{vx_mask?fmt=%s}.stat'
                    )
            else:
                if date_beg == date_end:
                    filename_template = (
                        filename_template+date_type.lower()+date_beg
                        )
                else:
                    filename_template = (
                        filename_template+date_type.lower()+
                        date_beg+'to'+date_end
                        )
                for loop_list in lists_to_loop:
                    if loop_list != 'MODEL_LIST':
                        list_name = loop_list.replace('_LIST', '')
                        if 'HOUR' in list_name:
                            filename_template = (
                                filename_template+'_'
                                +list_name.replace('_', '').lower()
                                +config_dict[list_name]+'Z'
                                )
                        else:
                            filename_template = (
                                filename_template+'_'
                                +list_name.replace('_', '').lower()
                                +config_dict[list_name].replace('"', '')
                                )
        self.logger.debug(
            "Building "+output_type+" filename from "+filename_type \
            +" template: "+filename_template
            )
        stringsub_dict = self.build_stringsub_dict(date_beg, date_end, 
                                                   date_type, lists_to_loop, 
                                                   lists_to_group, config_dict)
        ss = sts.StringSub(self.logger,
                           filename_template,
                           **stringsub_dict)
        output_filename = ss.do_string_sub()
        return output_filename

    def get_lookin_dir(self, dir_path, date_beg, date_end, date_type,
                       lists_to_loop, lists_to_group, config_dict):
        """!Fill in necessary information to get the path to
            the lookin directory to pass to stat_analysis.
             
             Args:
                 dir_path          - string of the user provided
                                     directory path
                 date_beg          - string of the beginning date in
                                     YYYYMMDD form
                 date_end          - string of the end date in YYYYMMDD
                                     form
                 date_type         - string of the date type, either
                                     VALID or INIT
                 lists_to_loop     - list of all the list names whose
                                     items are being grouped together
                 lists_to group    - list of all the list names whose
                                     items are being looped over
                 config_dict       - dictionary containing the
                                     configuration information

             Returns:
                 lookin_dir        - string of the filled directory
                                     from dir_path
        """
        if '?fmt=' in dir_path:
            stringsub_dict = self.build_stringsub_dict(date_beg, date_end, 
                                                       date_type, 
                                                       lists_to_loop, 
                                                       lists_to_group, 
                                                       config_dict)
            ss = sts.StringSub(self.logger,
                               dir_path,
                               **stringsub_dict)
            dir_path_filled = ss.do_string_sub()
        else:
            dir_path_filled = dir_path
        if '*' in dir_path_filled:
            dir_path_filled_all = (
                subprocess.check_output('ls -d '+dir_path_filled, 
                                        shell=True).rstrip('\n')
                )
        else:
            dir_path_filled_all = dir_path_filled
        lookin_dir = dir_path_filled_all
        return lookin_dir

    def format_valid_init(self, date_beg, date_end, date_type,
                          config_dict):
        """! Format the valid and initialization dates and
             hours for the MET stat_analysis config file.

             Args:
                 date_beg    - string of the beginning date in
                               YYYYMMDD form
                 date_end    - string of the end date in YYYYMMDD
                               form
                 date_type   - string of the date type, either
                               VALID or INIT
                 config_dict - dictionary containing the
                               configuration information

             Returns:
                 config_dict - dictionary containing the
                               edited configuration information
                               for valid and initialization dates
                               and hours 
        """
        fcst_valid_hour_list = config_dict['FCST_VALID_HOUR'].split(', ')
        fcst_init_hour_list = config_dict['FCST_INIT_HOUR'].split(', ')
        obs_valid_hour_list = config_dict['OBS_VALID_HOUR'].split(', ')
        obs_init_hour_list = config_dict['OBS_INIT_HOUR'].split(', ')
        nfcst_valid_hour = len(fcst_valid_hour_list)
        nfcst_init_hour = len(fcst_init_hour_list)
        nobs_valid_hour = len(obs_valid_hour_list)
        nobs_init_hour = len(obs_init_hour_list)
        if nfcst_valid_hour > 1:
            if date_type == 'VALID':
                fcst_valid_hour_beg = fcst_valid_hour_list[0].replace('"','')
		fcst_valid_hour_end = fcst_valid_hour_list[-1].replace('"','')
                config_dict['FCST_VALID_BEG'] = (
                    str(date_beg)+'_'+fcst_valid_hour_beg
                    )
                config_dict['FCST_VALID_END'] = (
                    str(date_end)+'_'+fcst_valid_hour_end
                    )
            elif date_type == 'INIT':
                config_dict['FCST_VALID_BEG'] = ''
                config_dict['FCST_VALID_END'] = ''
        elif nfcst_valid_hour == 1 and fcst_valid_hour_list != ['']:
            fcst_valid_hour_now = fcst_valid_hour_list[0]
            config_dict['FCST_VALID_HOUR'] = '"'+fcst_valid_hour_now+'"'
            if date_type == 'VALID':
                config_dict['FCST_VALID_BEG'] = (
                    str(date_beg)+'_'+fcst_valid_hour_now
                    )
                config_dict['FCST_VALID_END'] = (
                    str(date_end)+'_'+fcst_valid_hour_now
                    )
            elif date_type == 'INIT':
                config_dict['FCST_VALID_BEG'] = ''
                config_dict['FCST_VALID_END'] = ''
        else:
            config_dict['FCST_VALID_BEG'] = ''
            config_dict['FCST_VALID_END'] = ''
            config_dict['FCST_VALID_HOUR'] = ''
        if nfcst_init_hour > 1:
            if date_type == 'VALID':
                config_dict['FCST_INIT_BEG'] = ''
                config_dict['FCST_INIT_END'] = ''
            elif date_type == 'INIT':
                fcst_init_hour_beg = fcst_init_hour_list[0].replace('"','')
                fcst_init_hour_end = fcst_init_hour_list[-1].replace('"','')
                config_dict['FCST_INIT_BEG'] = (
                    str(date_beg)+'_'+fcst_init_hour_beg
                    )
                config_dict['FCST_INIT_END'] = (
                    str(date_end)+'_'+fcst_init_hour_end
                    )
        elif nfcst_init_hour == 1 and fcst_init_hour_list != ['']:
            fcst_init_hour_now = fcst_init_hour_list[0]
            config_dict['FCST_INIT_HOUR'] = '"'+fcst_init_hour_now+'"'
            if date_type == 'VALID':
                config_dict['FCST_INIT_BEG'] = ''
                config_dict['FCST_INIT_END'] = ''
            elif date_type == 'INIT':
                config_dict['FCST_INIT_BEG'] = (
                    str(date_beg)+'_'+fcst_init_hour_now
                    )
                config_dict['FCST_INIT_END'] = (
                    str(date_end)+'_'+fcst_init_hour_now
                    )
        else:
            config_dict['FCST_INIT_BEG'] = ''
            config_dict['FCST_INIT_END'] = ''
            config_dict['FCST_INIT_HOUR'] = ''
        if nobs_valid_hour > 1:
            if date_type == 'VALID':
                obs_valid_hour_beg = obs_valid_hour_list[0].replace('"','')
                obs_valid_hour_end = obs_valid_hour_list[-1].replace('"','')
                config_dict['OBS_VALID_BEG'] = (
                    str(date_beg)+'_'+obs_valid_hour_beg
                    )
                config_dict['OBS_VALID_END'] = (
                    str(date_end)+'_'+obs_valid_hour_end
                    )
            elif date_type == 'INIT':
                config_dict['OBS_VALID_BEG'] = ''
                config_dict['OBS_VALID_END'] = ''
        elif nobs_valid_hour == 1 and obs_valid_hour_list != ['']:
            obs_valid_hour_now = obs_valid_hour_list[0]
            config_dict['OBS_VALID_HOUR'] = '"'+obs_valid_hour_now+'"'
            if date_type == 'VALID':
                config_dict['OBS_VALID_BEG'] = (
                     str(date_beg)+'_'+obs_valid_hour_now
                     )
                config_dict['OBS_VALID_END'] = (
                     str(date_end)+'_'+obs_valid_hour_now
                     )
            elif date_type == 'INIT':
                config_dict['OBS_VALID_BEG'] = ''
                config_dict['OBS_VALID_END'] = ''
        else:
            config_dict['OBS_VALID_BEG'] = ''
            config_dict['OBS_VALID_END'] = ''
            config_dict['OBS_VALID_HOUR'] = ''
        if nobs_init_hour > 1:
            if date_type == 'VALID':
                config_dict['OBS_INIT_BEG'] = ''
                config_dict['OBS_INIT_END'] = ''
            elif date_type == 'INIT':
                obs_init_hour_beg = obs_init_hour_list[0].replace('"','')
                obs_init_hour_end = obs_init_hour_list[-1].replace('"','')
                config_dict['OBS_INIT_BEG'] = (
                    str(date_beg)+'_'+obs_init_hour_beg
                    )
                config_dict['OBS_INIT_END'] = (
                    str(date_end)+'_'+obs_init_hour_end
                    )
        elif nobs_init_hour == 1 and obs_init_hour_list != ['']:
            obs_init_hour_now = obs_init_hour_list[0]
            config_dict['OBS_INIT_HOUR'] = '"'+obs_init_hour_now+'"'
            if date_type == 'VALID':
                config_dict['OBS_INIT_BEG'] = ''
                config_dict['OBS_INIT_END'] = ''
            elif date_type == 'INIT':
                config_dict['OBS_INIT_BEG'] = (
                    str(date_beg)+'_'+obs_init_hour_now
                    )
                config_dict['OBS_INIT_END'] = (
                    str(date_end)+'_'+obs_init_hour_now
                    )
        else:
            config_dict['OBS_INIT_BEG'] = ''
            config_dict['OBS_INIT_END'] = ''
            config_dict['OBS_INIT_HOUR'] = ''
        return config_dict

    def thresh_format(self, thresh):
        """! Format threshold using symbols and
             letters.
 
             Args:
                 thresh         - string of the threshold
                
             Returns:
                 thresh_symbol  - string of threshold 
                                  formatted using symbols
                 thresh_letters - string of the threshold 
                                  formatted using letters
        """
        if 'ge' or '>=' in thresh:
            thresh_value = thresh.replace('ge', '').replace('>=', '')
            thresh_symbol = '>='+thresh_value
            thresh_letters = 'ge'+thresh_value
        elif 'gt' or '>' in thresh:
            thresh_value = thresh.replace('gt', '').replace('>', '')
            thresh_symbol = '>'+thresh_value
            thresh_letters = 'gt'+thresh_value
        elif 'le' or '<=' in thresh:
            thresh_value = thresh.replace('le', '').replace('<=', '')
            thresh_symbol = '<='+thresh_value
            thresh_letters = 'le'+thresh_value
        elif 'lt' or '<' in thresh:
            thresh_value = thresh.replace('lt', '').replace('<', '')
            thresh_symbol = '<'+thresh_value
            thresh_letters = 'lt'+thresh_value
        elif 'eq' or '==' in thresh:
            thresh_value = thresh.replace('eq', '').replace('==', '')
            thresh_symbol = '=='+thresh_value
            thresh_letters = 'eq'+thresh_value
        elif 'ne' or '!=' in thresh:
            thresh_value = thresh.replace('ne', '').replace('!=', '')
            thresh_symbol = '!='+thresh_value
            thresh_letters = 'ne'+thresh_value
        else:
             self.logger.error(
                 "Threshold operator in "+thresh+" is not valid."
                  )
             exit(1)
        return thresh_symbol, thresh_letters

    class ModelObj(object):
        __slots__ = 'name', 'reference_name', 'dir', 'obtype', \
                    'dump_row_filename_template', 'dump_row_filename_type', \
                    'out_stat_filename_template', 'out_stat_filename_type'

    def parse_model_info(self):
        """! Parse for model information.
             
             Args:
                
             Returns:
                 model_list - list of objects containing
                              model information
        """
        model_info_list = []
        all_conf = self.config.keys('config')
        model_indices = []
        regex = re.compile('MODEL(\d+)$')
        for conf in all_conf:
            result = regex.match(conf)
            if result is not None:
                model_indices.append(result.group(1))
        for m in model_indices:
            if self.config.has_option('config', 'MODEL'+m):
                model_name = self.config.getstr('config', 'MODEL'+m)
                model_reference_name = (
                    self.config.getstr('config', 'MODEL'+m+'_REFERENCE_NAME',
                                       model_name)
                    )
                if self.config.has_option('config',
                                          'MODEL'+m
                                          +'_STAT_ANALYSIS_LOOKIN_DIR'):
                    model_dir = (
                        self.config.getraw('config',
                                           'MODEL'+m
                                           +'_STAT_ANALYSIS_LOOKIN_DIR')
                        )
                else:
                    self.logger.error(
                        "MODEL"+m+"_STAT_ANALYSIS_LOOKIN_DIR was not set."
                        )
                    exit(1)
                if self.config.has_option('config', 'MODEL'+m+'_OBTYPE'):
                    model_obtype = (
                        self.config.getstr('config', 'MODEL'+m+'_OBTYPE')
                        )
                else:
                    self.logger.error("MODEL"+m+"_OBTYPE was not set.")
                    exit(1)
                for output_type in [ 'DUMP_ROW', 'OUT_STAT' ]:
                    if (self.config.has_option('filename_templates', 'MODEL'+m
                                               +'_STAT_ANALYSIS_'+output_type
                                               +'_TEMPLATE')):
                        model_filename_template = (
                            self.config.getraw('filename_templates', 
                                               'MODEL'+m+'_STAT_ANALYSIS_'
                                               +output_type+'_TEMPLATE')
                            )
                        if model_filename_template == '':
                            model_filename_template = (
                                '{model?fmt=%s}_{obtype?fmt=%s}_'
                                )
                            model_filename_type = 'default'
                        else:
                            model_filename_type = 'user'
                    else:
                        if (self.config.has_option('filename_templates',
                                                   'STAT_ANALYSIS_'
                                                   +output_type+'_TEMPLATE')):
                            model_filename_template = (
                                self.config.getraw('filename_templates',
                                                   'STAT_ANALYSIS_'
                                                   +output_type+'_TEMPLATE')
                                )
                            if model_filename_template == '':
                                model_filename_template = (
                                    '{model?fmt=%s}_{obtype?fmt=%s}_'
                                    )
                                model_filename_type = 'default'
                            else:
                                model_filename_type = 'user'
                        else:
                            model_filename_template = (
                                '{model?fmt=%s}_{obtype?fmt=%s}_'
                                )
                            model_filename_type = 'default'
                    if output_type == 'DUMP_ROW':
                         model_dump_row_filename_template = (
                             model_filename_template
                             )
                         model_dump_row_filename_type = model_filename_type
                    elif output_type == 'OUT_STAT':
                        if 'MakePlots' in self.c_dict['PROCESS_LIST']:
                            model_out_stat_filename_template = 'NA'
                            model_out_stat_filename_type = 'NA'
                        else:
                            model_out_stat_filename_template = (
                                model_filename_template
                                )
                            model_out_stat_filename_type = model_filename_type
            else:
                self.logger.error("MODEL"+m+" was not set.")
                exit(1)
            mod = self.ModelObj()
            mod.name = model_name
            mod.reference_name = model_reference_name
            mod.dir = model_dir
            mod.obtype = model_obtype
            mod.dump_row_filename_template = model_dump_row_filename_template
            mod.dump_row_filename_type = model_dump_row_filename_type
            mod.out_stat_filename_template = model_out_stat_filename_template
            mod.out_stat_filename_type = model_out_stat_filename_type
            model_info_list.append(mod)
        return model_info_list, model_indices

    class FourierDecompObj(object):
        __slots__ = 'run_fourier', 'wave_num_pairings'

    def parse_var_fourier_decomp(self):
        """! Parse variable information for Fourier decomposition.
             
             Args:
                
             Returns:
                 fourier_decom_list - list of objects containing
                                      Fourier decomposition information
                                      for the variables
        """
        fourier_decom_list = []
        all_conf = self.config.keys('config')
        indices = []
        regex = re.compile('FCST_VAR(\d+)_NAME')
        for conf in all_conf:
            result = regex.match(conf)
            if result is not None:
                indices.append(result.group(1))
        for n in indices:
            if self.config.has_option('config', 'FCST_VAR'+n+'_NAME'):
                levels = util.getlist(
                    self.config.getstr('config', 'FCST_VAR'+n+'_LEVELS')
                    )
                run_fourier = (
                    self.config.getbool('config', 'VAR'+n+'_FOURIER_DECOMP', 
                                        False)
                    )
                fourier_wave_num_pairs = util.getlist(
                    self.config.getstr('config', 'VAR'+n+'_WAVE_NUM_LIST', 
                                       '')
                    )
                if run_fourier == False:
                    fourier_wave_num_pairs = ''
                for level in levels:
                    fd = self.FourierDecompObj()
                    fd.run_fourier = run_fourier
                    fd.wave_num_pairings = fourier_wave_num_pairs
                    fourier_decom_list.append(fd)
        return fourier_decom_list

    def parse_var_units(self):
        """! Parse variable information for variable units
             
             Args:
                
             Returns:
                 fcst_var_units_list - list of variable units
                                       for the forecast variables
                 obs_var_units_list  - list of variable units
                                       for the observation variables
        """
        fcst_units_list = []
        obs_units_list = []
        all_conf = self.config.keys('config')
        indices = []
        regex = re.compile('FCST_VAR(\d+)_NAME')
        for conf in all_conf:
            result = regex.match(conf)
            if result is not None:
                indices.append(result.group(1))
        for n in indices:
            fcst_units = self.config.getstr('config', 'FCST_VAR'+n+'_UNITS',
                                            '')
            obs_units = self.config.getstr('config', 'FCST_VAR'+n+'_UNITS', 
                                           '')
            if len(obs_units) == 0 and len(fcst_units) != 0:
                obs_units = fcst_units
            if len(fcst_units) == 0 and len(obs_units) != 0:
                fcst_units = obs_units
            fcst_units_list.append(fcst_units)
            obs_units_list.append(obs_units)
        return fcst_units_list, obs_units_list    

    def run_stat_analysis_job(self, date_beg, date_end, date_type):
        """! This runs stat_analysis over a period of valid
             or initialization dates for a job defined by
             the user.
              
             Args:
                 date_beg    - string of the beginning date in
                               YYYYMMDD form
                 date_end    - string of the end date in YYYYMMDD
                               form
                 date_type   - string of the date type, either
                               VALID or INIT
            
             Returns:

        """
        self.c_dict['JOB_NAME'] = self.config.getstr('config', 
                                                     'STAT_ANALYSIS_JOB_NAME')
        self.c_dict['JOB_ARGS'] = self.config.getstr('config', 
                                                     'STAT_ANALYSIS_JOB_ARGS')
        self.c_dict['VAR_LIST'] = util.parse_var_list(self.config)
        self.c_dict['FCST_VAR_LIST'] = util.getlist(
            self.config.getstr('config', 'FCST_VAR_LIST', '')
            )
        self.c_dict['OBS_VAR_LIST'] = util.getlist(
            self.config.getstr('config', 'OBS_VAR_LIST', '')
            )
        self.c_dict['FCST_UNITS_LIST'] = util.getlist(
            self.config.getstr('config', 'FCST_UNITS_LIST', '')
            )
        self.c_dict['OBS_UNITS_LIST'] = util.getlist(
            self.config.getstr('config', 'OBS_UNITS_LIST', '')
            )
        self.c_dict['FCST_LEVEL_LIST'] = util.getlist(
            self.config.getstr('config', 'FCST_LEVEL_LIST', '')
            )
        self.c_dict['OBS_LEVEL_LIST'] = util.getlist(
            self.config.getstr('config', 'OBS_LEVEL_LIST', '')
            )
        self.c_dict['FCST_THRESH_LIST'] = util.getlist(
            self.config.getstr('config', 'FCST_THRESH_LIST', '')
            )
        self.c_dict['OBS_THRESH_LIST'] =  util.getlist(
            self.config.getstr('config', 'OBS_THRESH_LIST', '')
            ) 
        # Do some preprocessing, formatting, and gathering
        # of config information.
        formatted_c_dict = copy.deepcopy(self.c_dict)
        model_info_list, model_indices = self.parse_model_info()
        if self.c_dict['MODEL_LIST'] == []:
            if model_indices > 0:
                self.logger.warning(
                    "MODEL_LIST was left blank, creating with MODELn " \
                    "information."
                    )
                model_name_list = []
                for model_info in model_info_list:
                    model_name_list.append(model_info.name)
                formatted_c_dict['MODEL_LIST'] = model_name_list
            else:
                self.logger.error("No model information was found.")
                exit(1)
        for fcst_valid_hour in self.c_dict['FCST_VALID_HOUR_LIST']:
            index = self.c_dict['FCST_VALID_HOUR_LIST'].index(fcst_valid_hour)
            formatted_c_dict['FCST_VALID_HOUR_LIST'][index] = (
                fcst_valid_hour.ljust(6,'0')
                )
        for fcst_init_hour in self.c_dict['FCST_INIT_HOUR_LIST']:
            index = self.c_dict['FCST_INIT_HOUR_LIST'].index(fcst_init_hour)
            formatted_c_dict['FCST_INIT_HOUR_LIST'][index] = (
                fcst_init_hour.ljust(6,'0')
                )
        for obs_valid_hour in self.c_dict['OBS_VALID_HOUR_LIST']:
            index = self.c_dict['OBS_VALID_HOUR_LIST'].index(obs_valid_hour)
            formatted_c_dict['OBS_VALID_HOUR_LIST'][index] = (
                obs_valid_hour.ljust(6,'0')
                )
        for obs_init_hour in self.c_dict['OBS_INIT_HOUR_LIST']:
            index = self.c_dict['OBS_INIT_HOUR_LIST'].index(obs_init_hour)
            formatted_c_dict['OBS_INIT_HOUR_LIST'][index] = (
                obs_init_hour.ljust(6,'0')
                )
        for fcst_lead in self.c_dict['FCST_LEAD_LIST']:
            index = self.c_dict['FCST_LEAD_LIST'].index(fcst_lead)
            formatted_c_dict['FCST_LEAD_LIST'][index] = (
                fcst_lead.ljust(6,'0')
                )
        for obs_lead in self.c_dict['OBS_LEAD_LIST']:
            index = self.c_dict['OBS_LEAD_LIST'].index(obs_lead)
            formatted_c_dict['OBS_LEAD_LIST'][index] = (
                obs_lead.ljust(6,'0')
                )
        # Parse whether all expected METplus config _LIST variables
        # to be treated as a loop or group.
        config_lists_to_group_items = formatted_c_dict['GROUP_LIST_ITEMS']
        config_lists_to_loop_items = formatted_c_dict['LOOP_LIST_ITEMS']
        lists_to_group_items, lists_to_loop_items = (
            self.set_lists_loop_or_group(config_lists_to_group_items, 
                                         config_lists_to_loop_items,
                                         formatted_c_dict)
            )
        runtime_setup_dict = {}
        # Fill setup dictionary for MET config variable name
        # and its value as a string for group lists.
        for list_to_group_items in lists_to_group_items:
            runtime_setup_dict_name = list_to_group_items.replace('_LIST', '')
            runtime_setup_dict_value = (
                [self.list_to_str(formatted_c_dict[list_to_group_items])]
                )
            runtime_setup_dict[runtime_setup_dict_name] = (
                runtime_setup_dict_value
                )
        # Fill setup dictionary for MET config variable name
        # and its value as a list for loop lists. Some items
        # in lists need to be formatted now, others done later.
        format_later_list = [
            'MODEL_LIST', 'FCST_VALID_HOUR_LIST', 'OBS_VALID_HOUR_LIST',
            'FCST_INIT_HOUR_LIST','OBS_INIT_HOUR_LIST'
             ]
        for list_to_loop_items in lists_to_loop_items:
            if list_to_loop_items not in format_later_list:
                for item in formatted_c_dict[list_to_loop_items]:
                    index = formatted_c_dict[list_to_loop_items].index(item)
                    formatted_c_dict[list_to_loop_items][index] = '"'+item+'"'
            runtime_setup_dict_name = list_to_loop_items.replace('_LIST', '')
            runtime_setup_dict_value = formatted_c_dict[list_to_loop_items]
            runtime_setup_dict[runtime_setup_dict_name] = (
                runtime_setup_dict_value
                )
        # Create run time dictionary with all the combinations
        # of settings to be run. 
        runtime_setup_dict_names = sorted(runtime_setup_dict)
        runtime_settings_dict_list = (
            [dict(zip(runtime_setup_dict_names, prod)) for prod in
             itertools.product(*(runtime_setup_dict[name] for name in
             runtime_setup_dict_names))]
             )
        # Loop over run settings.
        for runtime_settings_dict in runtime_settings_dict_list:
            self.parm = self.c_dict['CONFIG_FILE']
            # Set up stat_analysis -lookin argument, model and obs information
            # and stat_analysis job.
            job = '-job '+self.c_dict['JOB_NAME']+' '+self.c_dict['JOB_ARGS']
            nmodels = len(runtime_settings_dict['MODEL'].split(', '))
            if nmodels == 1:
                for m in model_indices:
                    model_check = runtime_settings_dict['MODEL'] \
                        .replace('"', '')
                    if self.config.getstr('config', 'MODEL'+m) == model_check:
                        break
                model_info = model_info_list[int(m)-1]
                runtime_settings_dict['MODEL'] = '"'+model_info.name+'"'
                runtime_settings_dict['OBTYPE'] = '"'+model_info.obtype+'"'
                lookin_dir = self.get_lookin_dir(model_info.dir, date_beg,
                                                 date_end, date_type, 
                                                 lists_to_loop_items, 
                                                 lists_to_group_items,
                                                 runtime_settings_dict)
                if '-dump_row' in self.c_dict['JOB_ARGS']:
                    dump_row_filename_template = (
                        model_info.dump_row_filename_template
                        )
                    dump_row_filename_type = model_info.dump_row_filename_type
                if '-out_stat' in self.c_dict['JOB_ARGS']:
                    out_stat_filename_template = (
                        model_info.out_stat_filename_template
                        )
                    out_stat_filename_type = model_info.out_stat_filename_type
            else:
                lookin_dir = ''
                model_list = []
                obtype_list = []
                for m in model_indices:
                    model_info = model_info_list[int(m)-1]
                    model_list.append(model_info.name)
                    obtype_list.append(model_info.obtype)
                    lookin_dir_m = self.get_lookin_dir(model_info.dir, 
                                                       date_beg, date_end,
                                                       date_type, 
                                                       lists_to_loop_items, 
                                                       lists_to_group_items,
                                                       runtime_settings_dict)
                    lookin_dir = lookin_dir+' '+lookin_dir_m
                runtime_settings_dict['MODEL'] = self.list_to_str(model_list)
                runtime_settings_dict['OBTYPE'] = self.list_to_str(obtype_list)
                if '-dump_row' in self.c_dict['JOB_ARGS']:
                    dump_row_filename_template = (
                        self.config.getraw('filename_templates',
                                           'STAT_ANALYSIS_DUMP_ROW_TEMPLATE',
                                           '')
                        )
                    if dump_row_filename_template == '':
                        dump_row_filename_type = 'default'
                    else:
                        dump_row_filename_type = 'user'
                if '-out_stat' in self.c_dict['JOB_ARGS']:
                    out_stat_filename_template = (
                        self.config.getraw('filename_templates',
                                           'STAT_ANALYSIS_OUT_STAT_TEMPLATE',
                                           '')
                        )
                    if out_stat_filename_template == '':
                        out_stat_filename_type = 'default'
                    else:
                        out_stat_filename_type = 'user'
            runtime_settings_dict['-lookin'] = lookin_dir
            self.set_lookin_dir(runtime_settings_dict['-lookin'])
            if '-dump_row' in self.c_dict['JOB_ARGS']:
                dump_row_filename = (
                    self.get_output_filename('dump_row', 
                                             dump_row_filename_template,
                                             dump_row_filename_type,
                                             date_beg, date_end,
                                             date_type, lists_to_loop_items, 
                                             lists_to_group_items,
                                             runtime_settings_dict)
                    )
                dump_row_file = (
                    self.c_dict['OUTPUT_BASE_DIR']+'/'+dump_row_filename
                    )
                job = job.replace('[dump_row_file]', dump_row_file)
                job = job.replace('[dump_row_filename]', dump_row_file)
                dump_row_output_dir = dump_row_file.rpartition('/')[0]
                if not os.path.exists(dump_row_output_dir):
                   util.mkdir_p(dump_row_output_dir)
            if '-out_stat' in self.c_dict['JOB_ARGS']:
                out_stat_filename = (
                    self.get_output_filename('out_stat', 
                                             out_stat_filename_template,
                                             out_stat_filename_type,
                                             date_beg, date_end,
                                             date_type,lists_to_loop_items, 
                                             lists_to_group_items,
                                             runtime_settings_dict)
                    )
                out_stat_file = (
                    self.c_dict['OUTPUT_BASE_DIR']+'/'+out_stat_filename
                    )
                job = job.replace('[out_stat_file]', out_stat_file)
                job = job.replace('[out_stat_filename]', out_stat_file)
                out_stat_output_dir = out_stat_file.rpartition('/')[0]
                if not os.path.exists(out_stat_output_dir):
                   util.mkdir_p(out_stat_output_dir)
            runtime_settings_dict['JOB'] = job 
            # Set up forecast and observation valid
            # and initialization time information.
            runtime_settings_dict = (
                self.format_valid_init(date_beg, date_end, date_type, 
                                       runtime_settings_dict)
                )
            # Set environment variables and run stat_analysis.
            self.logger.debug("STAT_ANALYSIS RUN SETTINGS....")
            for name, value in runtime_settings_dict.items():
                self.add_env_var(name, value)
                self.logger.debug(name+": "+value)
            cmd = self.get_command()
            if cmd is None:
                self.logger.error("stat_analysis could not generate command")
                return
            self.build()
            self.clear()

    def filter_for_plotting(self):
        """! Special case for running stat_analysis over a period of 
             valid or initialization dates for a filter job, so 
             MakePlots can be run correctly following StatAnalysis.
             This method loops over MODEL_LIST, . 
             Args:

             Returns:

        """
        # Do checks for bad configuration file options.
        bad_config_variable_list = [
            'FCST_VAR_LIST', 'FCST_LEVEL_LIST', 
            'FCST_THRESH_LIST', 'FCST_UNITS_LIST',
            'OBS_VAR_LIST', 'OBS_LEVEL_LIST', 
            'OBS_THRESH_LIST', 'OBS_UNITS_LIST'
            ]
        for bad_config_variable in bad_config_variable_list:
            if self.config.has_option('config',
                                      bad_config_variable):
                self.logger.error(
                    "Bad config option for running StatAnalysis followed by " \
                    "MakePlots. Please remove "+bad_config_variable+" and " \
                    "set using FCST/OBS_VARn"
                    )
                exit(1)
        loop_group_accepted_options = [ 
            'FCST_VALID_HOUR_LIST', 'FCST_INIT_HOUR_LIST', 
            'OBS_VALID_HOUR_LIST', 'OBS_INIT_HOUR_LIST'
            ]
        for config_list in self.c_dict['GROUP_LIST_ITEMS']:
            if config_list not in loop_group_accepted_options:
                self.logger.error(
                    "Bad config option for running StatAnalysis followed by " \
                    "MakePlots. Only accepted values in GROUP_LIST_ITEMS " \
                    "are FCST_VALID_HOUR_LIST, FCST_INIT_HOUR_LIST, " \
                    "OBS_VALID_HOUR_LIST, OBS_INIT_HOUR_LIST. Found " \
                    +config_list
                    )
                exit(1) 
        for config_list in self.c_dict['LOOP_LIST_ITEMS']:
            if config_list not in loop_group_accepted_options:
                self.logger.error(
                    "Bad config option for running StatAnalysis followed by " \
                    "MakePlots. Only accepted values in LOOP_LIST_ITEMS " \
                    "are FCST_VALID_HOUR_LIST, FCST_INIT_HOUR_LIST, " \
                    "OBS_VALID_HOUR_LIST, OBS_INIT_HOUR_LIST. Found " \
                    +config_list
                    )
                exit(1)
        # Do checks for required configuration file options that are
        # defined by user.
        required_config_variable_list = [ 
            'VX_MASK_LIST', 'FCST_LEAD_LIST', 'LINE_TYPE_LIST' 
            ]
        for required_config_variable in required_config_variable_list:
            if len(self.c_dict[required_config_variable]) == 0:
                self.logger.error(
                    required_config_variable+" has no items. This list must "
                    +"have items to run StatAnalysis followed by MakePlots."
                )
                exit(1)
        # Do some preprocessing, formatting, and gathering
        # of config information.
        date_type = self.c_dict['DATE_TYPE']
        formatted_c_dict = copy.deepcopy(self.c_dict)
        model_info_list, model_indices = self.parse_model_info()
        if self.c_dict['MODEL_LIST'] == []:
            if model_indices > 0:
                self.logger.warning(
                    "MODEL_LIST was left blank, creating with MODELn " \
                    "information."
                    )
                model_name_list = []
                for model_info in model_info_list:
                    model_name_list.append(model_info.name)
                formatted_c_dict['MODEL_LIST'] = model_name_list
            else:
                self.logger.error("No model information was found.")
                exit(1)
        var_info_thresh_list = self.c_dict['VAR_LIST']
        var_info_list = []
        for var_info_thresh in var_info_thresh_list:
            if len(var_info_thresh['fcst_thresh']) > 0:
                for fcst_thresh in var_info_thresh['fcst_thresh']:
                    fo = util.FieldObj()
                    fo.fcst_name = var_info_thresh['fcst_name']
                    fo.obs_name = var_info_thresh['obs_name']
                    fo.fcst_extra = var_info_thresh['fcst_extra']
                    fo.obs_extra = var_info_thresh['obs_extra']
                    fo.fcst_level = var_info_thresh['fcst_level']
                    fo.obs_level = var_info_thresh['obs_level']
                    fo.index = var_info_thresh['index']
                    fcst_thresh_symbol, fcst_thresh_letters = (
                        self.thresh_format(fcst_thresh)
                        )
                    fo.fcst_thresh = [fcst_thresh_letters]
                    obs_thresh = (
                        var_info_thresh.obs_thresh[var_info_thresh \
                            .fcst_thresh.index(fcst_thresh)]
                    )
                    obs_thresh_symbol, obs_thresh_letters = (
                        self.thresh_format(obs_thresh)
                        )
                    fo.obs_thresh = [obs_thresh_letters]
                    var_info_list.append(fo)
            else:
                fo = util.FieldObj()
                fo.fcst_name = var_info_thresh['fcst_name']
                fo.obs_name = var_info_thresh['obs_name']
                fo.fcst_extra = var_info_thresh['fcst_extra']
                fo.obs_extra = var_info_thresh['obs_extra']
                fo.fcst_level = var_info_thresh['fcst_level']
                fo.obs_level = var_info_thresh['obs_level']
                fo.index = var_info_thresh['index']
                fo.fcst_thresh = var_info_thresh['fcst_thresh']
                fo.obs_thresh = var_info_thresh['obs_thresh']
                var_info_list.append(fo)
        fourier_decom_info_list = self.parse_var_fourier_decomp()
        fcst_units_list, obs_units_list = self.parse_var_units()   
        for fcst_valid_hour in self.c_dict['FCST_VALID_HOUR_LIST']:
            index = self.c_dict['FCST_VALID_HOUR_LIST'].index(fcst_valid_hour)
            formatted_c_dict['FCST_VALID_HOUR_LIST'][index] = (
                fcst_valid_hour.ljust(6,'0')
                )
        for fcst_init_hour in self.c_dict['FCST_INIT_HOUR_LIST']:
            index = self.c_dict['FCST_INIT_HOUR_LIST'].index(fcst_init_hour)
            formatted_c_dict['FCST_INIT_HOUR_LIST'][index] = (
                fcst_init_hour.ljust(6,'0')
                )
        for obs_valid_hour in self.c_dict['OBS_VALID_HOUR_LIST']:
            index = self.c_dict['OBS_VALID_HOUR_LIST'].index(obs_valid_hour)
            formatted_c_dict['OBS_VALID_HOUR_LIST'][index] = (
                obs_valid_hour.ljust(6,'0')
                )
        for obs_init_hour in self.c_dict['OBS_INIT_HOUR_LIST']:
            index = self.c_dict['OBS_INIT_HOUR_LIST'].index(obs_init_hour)
            formatted_c_dict['OBS_INIT_HOUR_LIST'][index] = (
                obs_init_hour.ljust(6,'0')
                )
        for fcst_lead in self.c_dict['FCST_LEAD_LIST']:
            index = self.c_dict['FCST_LEAD_LIST'].index(fcst_lead)
            formatted_c_dict['FCST_LEAD_LIST'][index] = (
                fcst_lead.ljust(6,'0')
                )
        for obs_lead in self.c_dict['OBS_LEAD_LIST']:
            index = self.c_dict['OBS_LEAD_LIST'].index(obs_lead)
            formatted_c_dict['OBS_LEAD_LIST'][index] = (
                obs_lead.ljust(6,'0')
                )
        output_base_dir = self.c_dict['OUTPUT_BASE_DIR']
        if not os.path.exists(output_base_dir):
            util.mkdir_p(output_base_dir)
        # Loop through variables and add information
        # to a special variable dictionary
        for var_info in var_info_list:
            var_fourier_decomp_info = fourier_decom_info_list[
                int(var_info.index)
                ]
            var_fcst_units = fcst_units_list[int(var_info.index)]
            var_obs_units = obs_units_list[int(var_info.index)]
            var_info_formatted_c_dict = copy.deepcopy(formatted_c_dict)
            var_info_formatted_c_dict['FCST_VAR_LIST'] = [ var_info.fcst_name ]
            var_info_formatted_c_dict['FCST_LEVEL_LIST'] = [ 
                var_info.fcst_level 
                ]
            var_info_formatted_c_dict['FCST_UNITS_LIST'] = [ var_fcst_units ]
            var_info_formatted_c_dict['OBS_VAR_LIST'] = [ var_info.obs_name ]
            var_info_formatted_c_dict['OBS_LEVEL_LIST'] = [ 
                var_info.obs_level 
                ]
            var_info_formatted_c_dict['OBS_UNITS_LIST'] = [ var_obs_units ]
            var_info_formatted_c_dict['FCST_THRESH_LIST'] = (
                var_info.fcst_thresh
                )
            var_info_formatted_c_dict['OBS_THRESH_LIST'] = (
                var_info.obs_thresh
                )
            if var_fourier_decomp_info.run_fourier:                 
                for pair in var_fourier_decomp_info.wave_num_pairings:
                    var_info_formatted_c_dict['INTERP_MTHD_LIST'] \
                    .append('WV1_'+pair)
            # Parse whether all expected METplus config _LIST variables
            # to be treated as a loop or group.
            config_lists_to_group_items = (
                var_info_formatted_c_dict['GROUP_LIST_ITEMS']
                )
            config_lists_to_loop_items = (
                var_info_formatted_c_dict['LOOP_LIST_ITEMS']
                )
            lists_to_group_items, lists_to_loop_items = (
                self.set_lists_loop_or_group(config_lists_to_group_items,
                                             config_lists_to_loop_items,
                                             var_info_formatted_c_dict)
                )
            runtime_setup_dict = {}
            # Fill setup dictionary for MET config variable name
            # and its value as a string for group lists.
            for list_to_group_items in lists_to_group_items:
                runtime_setup_dict_name = (
                    list_to_group_items.replace('_LIST', '')
                    )
                runtime_setup_dict_value = [
                    self.list_to_str(
                        var_info_formatted_c_dict[list_to_group_items]
                        )
                    ]
                runtime_setup_dict[runtime_setup_dict_name] = (
                    runtime_setup_dict_value
                    )
            # Fill setup dictionary for MET config variable name
            # and its value as a list for loop lists. Some items
            # in lists need to be formatted now, others done later.
            format_later_list = [
                'MODEL_LIST', 'FCST_VALID_HOUR_LIST', 'OBS_VALID_HOUR_LIST',
                'FCST_INIT_HOUR_LIST','OBS_INIT_HOUR_LIST'
                 ]
            for list_to_loop_items in lists_to_loop_items:
                runtime_setup_dict_name = list_to_loop_items.replace('_LIST', 
                                                                     '')
                if list_to_loop_items not in format_later_list:
                    for item in \
                             var_info_formatted_c_dict[list_to_loop_items]:
                        index = (
                            var_info_formatted_c_dict[list_to_loop_items] \
                            .index(item)
                            )
                        var_info_formatted_c_dict[list_to_loop_items][index] \
                            = '"'+item+'"'
                runtime_setup_dict_name = list_to_loop_items.replace('_LIST', 
                                                                     '')
                runtime_setup_dict_value = (
                    var_info_formatted_c_dict[list_to_loop_items]
                    )
                runtime_setup_dict[runtime_setup_dict_name] = (
                    runtime_setup_dict_value
                    )
            # Create run time dictionary with all the combinations
            # of settings to be run.
            runtime_setup_dict_names = sorted(runtime_setup_dict)
            runtime_settings_dict_list = (
                [dict(zip(runtime_setup_dict_names, prod)) for prod in
                itertools.product(*(runtime_setup_dict[name] for name in
                runtime_setup_dict_names))]
                )
            # Loop over run settings.
            for runtime_settings_dict in runtime_settings_dict_list:
                self.parm = self.c_dict['CONFIG_FILE']
                # Set up stat_analysis -lookin argument, model and obs
                # information and stat_analysis job.
                job = '-job filter -dump_row '
                for m in model_indices:
                    model_check = runtime_settings_dict['MODEL'] \
                        .replace('"', '')
                    if (self.config.getstr('config', 'MODEL'+m) 
                            == model_check):
                        break
                model_info = model_info_list[int(m)-1]
                runtime_settings_dict['MODEL'] = '"'+model_info.name+'"'
                runtime_settings_dict['OBTYPE'] = '"'+model_info.obtype+'"'
                lookin_dir = self.get_lookin_dir(model_info.dir, 
                                                 self.c_dict[date_type+'_BEG'],
                                                 self.c_dict[date_type+'_END'],
                                                 date_type, 
                                                 lists_to_loop_items,
                                                 lists_to_group_items,
                                                 runtime_settings_dict)
                runtime_settings_dict['-lookin'] = lookin_dir
                self.set_lookin_dir(runtime_settings_dict['-lookin'])
                dump_row_filename_template = (
                    model_info.dump_row_filename_template
                    )
                dump_row_filename_type = model_info.dump_row_filename_type
                dump_row_filename = (
                    self.get_output_filename('dump_row', 
                                             dump_row_filename_template, 
                                             dump_row_filename_type,
                                             self.c_dict[date_type+'_BEG'],
                                             self.c_dict[date_type+'_END'],
                                             date_type, lists_to_loop_items, 
                                             lists_to_group_items,
                                             runtime_settings_dict)
                    )
                dump_row_file = (
                    self.c_dict['OUTPUT_BASE_DIR']+'/'+dump_row_filename
                    )
                dump_row_output_dir = dump_row_file.rpartition('/')[0]
                if not os.path.exists(dump_row_output_dir):
                   util.mkdir_p(dump_row_output_dir)
                runtime_settings_dict['JOB'] = job+dump_row_file
                # Set up forecast and observation valid and 
                # initialization time information.
                runtime_settings_dict = (
                    self.format_valid_init(self.c_dict[date_type+'_BEG'], 
                                           self.c_dict[date_type+'_END'], 
                                           date_type, 
                                           runtime_settings_dict)
                    )
                # Set environment variables and run stat_analysis.
                self.logger.debug("STAT_ANALYSIS RUN SETTINGS....")
                for name, value in runtime_settings_dict.items():
                    self.add_env_var(name, value)
                    self.logger.debug(name+": "+value)
                cmd = self.get_command()
                if cmd is None:
                    self.logger.error(
                        "stat_analysis could not generate command"
                        )
                    return
                self.build()
                self.clear()

    def run_all_times(self):
        self.c_dict['DATE_TYPE'] = self.config.getstr('config', 'DATE_TYPE')
        self.c_dict['VALID_BEG'] = self.config.getstr('config', 'VALID_BEG',
                                                                '')
        self.c_dict['VALID_END'] = self.config.getstr('config', 'VALID_END',
                                                      '')
        self.c_dict['INIT_BEG'] = self.config.getstr('config', 'INIT_BEG', '')
        self.c_dict['INIT_END'] = self.config.getstr('config', 'INIT_END', '')
        date_type = self.c_dict['DATE_TYPE']
        if date_type not in [ 'VALID', 'INIT' ]:
            self.logger.error("DATE_TYPE must be VALID or INIT")
            exit(1)
        if 'MakePlots' in self.c_dict['PROCESS_LIST']:
            self.filter_for_plotting()
        else:
            date_beg = self.c_dict[date_type+'_BEG']
            date_end = self.c_dict[date_type+'_END']
            self.run_stat_analysis_job(date_beg, date_end, date_type)

    def run_at_time(self, input_dict):
        loop_by = self.config.getstr('config', 'LOOP_BY')
        if loop_by in [ 'VALID', 'INIT' ]:
            date = input_dict[loop_by.lower()].strftime('%Y%m%d')
            self.run_stat_analysis_job(date, date, loop_by)
        else:
            self.logger.error("LOOP_BY must be VALID or INIT")
            exit(1)
