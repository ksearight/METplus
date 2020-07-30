#!/usr/bin/env python

"""tc_gen
Program Name: tc_gen_wrapper.py
Contact(s): George McCabe
Abstract: Builds command for and runs tc_gen
History Log:  Initial version
Usage:
Parameters: None
Input Files:
Output Files: nc files
Condition codes: 0 for success, 1 for failure
"""

import os

from ..util import met_util as util
from ..util import time_util
from . import CommandBuilder
from ..util import do_string_sub

'''!@namespace TCGenWrapper
@brief Wraps the TC-Gen tool
@endcode
'''


class TCGenWrapper(CommandBuilder):
    def __init__(self, config, logger):
        self.app_name = "tc_gen"
        self.app_path = os.path.join(config.getdir('MET_BIN_DIR'),
                                     self.app_name)
        super().__init__(config, logger)

    def create_c_dict(self):
        c_dict = super().create_c_dict()
        c_dict['VERBOSITY'] = self.config.getstr('config', 'LOG_TC_GEN_VERBOSITY',
                                                 c_dict['VERBOSITY'])
        c_dict['ALLOW_MULTIPLE_FILES'] = True
        c_dict['CONFIG_FILE'] = self.config.getraw('config', 'TC_GEN_CONFIG_FILE', '')

        c_dict['GENESIS_INPUT_DIR'] = self.config.getdir('TC_GEN_GENESIS_INPUT_DIR', '')
        c_dict['GENESIS_INPUT_TEMPLATE'] = self.config.getraw('filename_templates',
                                                              'TC_GEN_GENESIS_INPUT_TEMPLATE')

        c_dict['OUTPUT_DIR'] = self.config.getdir('TC_GEN_OUTPUT_DIR', '')
        c_dict['OUTPUT_TEMPLATE'] = self.config.getraw('filename_templates',
                                                       'TC_GEN_OUTPUT_TEMPLATE')

        c_dict['TRACK_INPUT_DIR'] = self.config.getdir('TC_GEN_TRACK_INPUT_DIR', '')
        c_dict['TRACK_INPUT_TEMPLATE'] = self.config.getraw('filename_templates',
                                                            'TC_GEN_TRACK_INPUT_TEMPLATE')


        # values used in configuration file

        conf_value = self.config.getstr('config', 'TC_GEN_STORM_ID', '')
        if conf_value:
            c_dict['STORM_ID'] = f'storm_id = "{conf_value}";'

        conf_value = self.config.getstr('config',
                                        'TC_GEN_VALID_BEG',
                                        self.config.getstr('config',
                                                           'VALID_BEG',
                                                           ''))
        if conf_value:
            c_dict['VALID_BEG'] = f'valid_beg = "{conf_value}";'

        conf_value = self.config.getstr('config',
                                        'TC_GEN_VALID_END',
                                        self.config.getstr('config',
                                                           'VALID_END',
                                                           ''))
        if conf_value:
            c_dict['VALID_END'] = f'valid_end = "{conf_value}";'

        conf_value = util.getlist(self.config.getstr('config',
                                                     'TC_GEN_INIT_HOUR_LIST',
                                                     ''))
        if conf_value:
            conf_list = str(conf_value).replace("'", '"')
            c_dict['INIT_HOUR_LIST'] = f"init_hour = {conf_list};"

        return c_dict

    def set_environment_variables(self, time_info):
        """!Set environment variables that will be read by the MET config file.
            Reformat as needed. Print list of variables that were set and their values.
            Args:
              @param time_info dictionary containing timing info from current run"""

        self.add_env_var('MODEL',
                         self.c_dict.get('MODEL', ''))

        self.add_env_var('STORM_ID',
                         self.c_dict.get('STORM_ID', ''))

        self.add_env_var('VALID_BEG',
                         self.c_dict.get('VALID_BEG', ''))

        self.add_env_var('VALID_END',
                         self.c_dict.get('VALID_END', ''))

        self.add_env_var('INIT_HOUR_LIST',
                         self.c_dict.get('INIT_HOUR_LIST', ''))

        self.add_env_var('LEAD_LIST',
                         self.c_dict.get('LEAD_LIST', ''))

        super().set_environment_variables(time_info)

    def get_command(self):
        cmd = self.app_path

        # add genesis
        cmd += ' -genesis ' + self.c_dict['GENESIS']

        # add track
        cmd += ' -track ' + self.c_dict['TRACK']

        # add arguments
        cmd += ' ' + ' '.join(self.args)

        # add output path
        out_path = self.get_output_path()
        cmd += ' -out ' + out_path

        parent_dir = os.path.dirname(out_path)
        if not parent_dir:
            self.log_error('Must specify path to output file')
            return None

        # create full output dir if it doesn't already exist
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)

        # add verbosity
        cmd += f" -v {self.c_dict['VERBOSITY']}"
        return cmd

    def run_at_time(self, input_dict):
        """! Runs the MET application for a given run time. This function
              loops over the list of forecast leads and runs the application for
              each.
              Args:
                @param input_dict dictionary containing timing information
        """
        for custom_string in self.c_dict['CUSTOM_LOOP_LIST']:
            if custom_string:
                self.logger.info(f"Processing custom string: {custom_string}")

            input_dict['custom'] = custom_string

            time_info = time_util.ti_calculate(input_dict)

            if util.skip_time(time_info, self.c_dict.get('SKIP_TIMES', {})):
                self.logger.debug('Skipping run time')
                continue

            self.run_at_time_once(time_info)

    def run_at_time_once(self, time_info):
        """! Process runtime and try to build command to run ascii2nc
             Args:
                @param time_info dictionary containing timing information
        """
        # get input files
        if self.find_input_files(time_info) is None:
            return

        # get output path
        if not self.find_and_check_output_file(time_info):
            return

        # get other configurations for command
        self.set_command_line_arguments(time_info)

        # set environment variables if using config file
        self.set_environment_variables(time_info)

        # build command and run
        self.build_and_run_command()

    def find_input_files(self, time_info):
        """!Get DECK file and list of input data files and set c_dict items.
            Args:
                @param time_info time dictionary to use for string substitution
                @returns Input file list if all files were found, None if not.
        """
        # get track file or directory
        track_template = os.path.join(self.c_dict['TRACK_INPUT_DIR'],
                                      self.c_dict['TRACK_INPUT_TEMPLATE'])
        track_file = do_string_sub(track_template,
                                   **time_info)
#        track_file = do_string_sub(self.c_dict['TRACK_INPUT_TEMPLATE'],
#                                   time_info)
#        track_file = os.path.join(self.c_dict['TRACK_INPUT_DIR'],
#                                  track_file)

        self.c_dict['TRACK'] = track_file
        self.logger.debug(f"Found track: {track_file}")

        # get genesis file or directory
        genesis_template = os.path.join(self.c_dict['GENESIS_INPUT_DIR'],
                                        self.c_dict['GENESIS_INPUT_TEMPLATE'])
        genesis_file = do_string_sub(genesis_template,
                                     **time_info)

        self.c_dict['GENESIS'] = genesis_file
        self.logger.debug(f"Found genesis: {genesis_file}")

        # set LEAD_LIST to list of forecast leads used
        lead_seq = util.get_lead_sequence(self.config, time_info)
        if lead_seq != [0]:
            lead_list = []
            for lead in lead_seq:
                lead_hours = (
                    time_util.ti_get_seconds_from_relativedelta(lead,
                                                                valid_time=time_info['valid'])
                    ) // 3600
                lead_list.append(f'"{str(lead_hours).zfill(2)}"')

            self.c_dict['LEAD_LIST'] = f"lead = [{', '.join(lead_list)}];"

        return True

    def set_command_line_arguments(self, time_info):

        # add config file - passing through do_string_sub to get custom string if set
        config_file = do_string_sub(self.c_dict['CONFIG_FILE'],
                                    **time_info)
        self.args.append(f"-config {config_file}")

if __name__ == "__main__":
    util.run_stand_alone(__file__, "TCRMW")
