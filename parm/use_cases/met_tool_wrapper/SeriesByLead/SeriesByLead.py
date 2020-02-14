"""
SeriesByLead
============

This METplus SeriesByLead use case will run the MET Series Analysis tool. 

This example performs a series analysis on an entire range of forecast hours.
that is, all forecast hours VS. by forecast hour grouping.

Performing series analysis for all forecast hours, performs a series analysis 
by lead time, based on a range and increment of forecast hours.

It performs a series analysis of paired data based on lead time and 
generates plots for each requested variable and statistic, as specified in 
the configuration file.

It Performs any optional filtering of input tcst data with MET tc_stat 
then performs regridding via MET regrid_data_plane, then builds up
the commands to perform a series analysis by LEAD time by invoking the
MET series_analysis tool. NetCDF plots are generated by invoking the MET tool
plot_data_plane. The NetCDF plots are then converted to .png and Postscript,
and an animated GIF representative of the entire series is generated.

"""

###########################################
# Scientific Objective
# --------------------
#
# By grouping the statistical information by lead time
# as a series (as opposed to grouping by geographical/grid locations), model
# differences specific to weather systems and changes in accuracy over a range of
# lead times can be discovered.

##############################################################################
# Datasets
# --------
#
#
# Input is the output of ExtractTiles, SERIES_ANALYSIS_INPUT_DIR.
#
# | **Forecast:** 
# |     extract_tiles/20141214_00
# | **Observation:** N/A
#
# | **Location:** All of the input data required for this use case can be found in the sample data tarball. Click here to the METplus releases page and download sample data for the appropriate release: https://github.com/NCAR/METplus/releases
# | The tarball should be unpacked into the directory that you will set the value of INPUT_BASE. See 'Running METplus' section for more information.
#
# | **Data Source:** Unknown

##############################################################################
# METplus Components
# ------------------
#
# This use case utilizes the METplus SeriesByLead wrapper to search for
# files that are valid at a given run time and generate a command to run
# the MET tool series_analysis.
#
# Typically, running SeriesByLead, will involve running the following METplus
# wrapper tasks in the following order, TcPairs, ExtractTiles, SeriesByLead.
# However, this use case example will run only SeriesByLead, therefore it
# uses sample data input from the output of already having run ExtractTiles. 

##############################################################################
# METplus Workflow
# ----------------
#
# Running SeriesByLead invokes the following MET tools: tc_stat, regrid_dataplane, 
# plot_data_plane and the following executables: ncap2, ncdump, and convert.
#
# This example processes the following run times:
#
# | **Init:** 2014-12-14_00Z

##############################################################################
# METplus Configuration
# ---------------------
#
# METplus first loads all of the configuration files found in parm/metplus_config,
# then it loads any configuration files passed to METplus via the command line
# with the -c option, i.e. -c /path/to/SeriesByLead.conf
#
# .. highlight:: bash
# .. literalinclude:: ../../../../parm/use_cases/met_tool_wrapper/SeriesByLead/SeriesByLead.conf

##############################################################################
# MET Configuration
# ---------------------
#
# METplus sets environment variables based on the values in the METplus configuration file.
# These variables are referenced in the MET configuration file. **YOU SHOULD NOT SET ANY OF THESE ENVIRONMENT VARIABLES YOURSELF! THEY WILL BE OVERWRITTEN BY METPLUS WHEN IT CALLS THE MET TOOLS!** If there is a setting in the MET configuration file that is not controlled by an environment variable, you can add additional environment variables to be set only within the METplus environment using the [user_env_vars] section of the METplus configuration files. See the 'User Defined Config' section on the 'System Configuration' page of the METplus User's Guide for more information.
#
# .. highlight:: bash
# .. literalinclude:: ../../../../parm/met_config/SeriesAnalysisConfig_wrapped
#
# Note the following variables are referenced in the MET configuration file.
#
# * **${REGRID_TO_GRID}** - Corresponds to SERIES_ANALYSIS_REGRID_TO_GRID in the METplus configuration file.
# * **${NAME}** - forecast or obs field information. Generated from BOTH_VAR<n>_NAME in the METplus configuration file.
# * **${LEVEL}** - forecast or obs field information. Generated from BOTH_VAR<n>_LEVELS in the METplus configuration file.
# * **${STAT_LIST}** - Corresponds to SERIES_ANALYSIS_STAT_LIST in the METplus configuration file.


##############################################################################
# Running METplus
# ---------------
#
# It is recommended to run this use case by:
#
# Passing in SeriesByLead.conf then a user-specific system configuration file::
#
#   master_metplus.py -c /path/to/SeriesByLead.conf -c /path/to/user_system.conf
#
# The following METplus configuration variables must be set correctly to run this example.:
#
# * **INPUT_BASE** - Path to directory where sample data tarballs are unpacked (See Datasets section to obtain tarballs).
# * **OUTPUT_BASE** - Path where METplus output will be written. This must be in a location where you have write permissions
# * **MET_INSTALL_DIR** - Path to location where MET is installed locally
#
# Example User Configuration File::
#
#   [dir]
#   INPUT_BASE = /path/to/sample/input/data
#   OUTPUT_BASE = /path/to/output/dir
#   MET_INSTALL_DIR = /path/to/met-X.Y 
#
# **NOTE:** All of these items must be found under the [dir] section.
#

##############################################################################
# Expected Output
# ---------------
#
# A successful run will output the following both to the screen and to the logfile::
#
#   INFO: METplus has successfully finished running.
#
# Refer to the value set for **OUTPUT_BASE** to find where the output data was generated.
# Output for this use case will be found in **SERIES_ANALYSIS_OUTPUT_DIR** (relative to **OUTPUT_BASE**)
# and will contain the following files:
#
# * series_animate/
#
#   * series_animate_HGT_P500_FBAR.gif
#   * series_animate_HGT_P500_ME.gif
#   * series_animate_HGT_P500_OBAR.gif
#   * series_animate_HGT_P500_TOTAL.gif
#   * series_animate_TMP_P850_FBAR.gif
#   * series_animate_TMP_P850_ME.gif
#   * series_animate_TMP_P850_OBAR.gif
#   * series_animate_TMP_P850_TOTAL.gif
#
# * series_F006/
#
#   * ANLY_FILES_F006
#   * FCST_FILES_F006
#   * series_F006_HGT_P500_FBAR.png
#   * series_F006_HGT_P500_FBAR.ps
#   * series_F006_HGT_P500_ME.png
#   * series_F006_HGT_P500_ME.ps
#   * series_F006_HGT_P500.nc
#   * series_F006_HGT_P500_OBAR.png
#   * series_F006_HGT_P500_OBAR.ps
#   * series_F006_HGT_P500_TOTAL.png
#   * series_F006_HGT_P500_TOTAL.ps
#   * series_F006_TMP_P850_FBAR.png
#   * series_F006_TMP_P850_FBAR.ps
#   * series_F006_TMP_P850_ME.png
#   * series_F006_TMP_P850_ME.ps
#   * series_F006_TMP_P850.nc
#   * series_F006_TMP_P850_OBAR.png
#   * series_F006_TMP_P850_OBAR.ps
#   * series_F006_TMP_P850_TOTAL.png
#   * series_F006_TMP_P850_TOTAL.ps
#
# * series_F012/
#
#   * Same list as in F006 but with F012
#
# * series_F018/
#
#   * Same list as in F006 but with F018

##############################################################################
# Keywords
# --------
#
# .. note:: `SeriesByLeadUseCase <https://ncar.github.io/METplus/search.html?q=SeriesByLeadUseCase&check_keywords=yes&area=default>`_,  `SeriesAnalysisUseCase <https://ncar.github.io/METplus/search.html?q=SeriesAnalysisUseCase&check_keywords=yes&area=default>`_

