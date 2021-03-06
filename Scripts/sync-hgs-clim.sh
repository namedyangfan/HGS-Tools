#!/bin/bash
# a rsync-based script to synchronize climate forcing data for HGS with a remote host, 
# while maintaining the original folder structure of the local source

# pre-process arguments using getopt
if [ -z $( getopt -T ) ]; then
  TMP=$( getopt -o qdn:p:h --long niceness:,project:,source:,dest:,quiet,debug,config:,data-root:,yaml,overwrite,help -n "$0" -- "$@" ) # pre-process arguments
  [ $? != 0 ] && exit 1 # getopt already prints an error message
  eval set -- "$TMP" # reset positional parameters (arguments) to $TMP list
fi # check if GNU getopt ("enhanced")
# parse arguments
VERBOSITY=1
NICENESS=0
#YAML=" --include '*.yaml'"
#while getopts 'fs' OPTION; do # getopts version... supports only short options
while true; do
  case "$1" in
    -n | --niceness      )   NICENESS=$2; shift 2;;
    -p | --project       )   PROJECT="$2"; shift 2;;
         --source        )   SRC="$2"; shift 2;;
         --dest          )   DST="$2"; shift 2;;
    -q | --quiet         )   VERBOSITY=0; shift;;
    -d | --debug         )   VERBOSITY=2; shift;;
         --config        )   KCFG="$2"; shift 2;;
         --data-root     )   DATA_ROOT="$2"; shift 2;;
         --yaml          )   YAML='*.yaml'; shift;;
         --overwrite     )   OVERWRITE='OVERWRITE'; shift 2;;
    -h | --help          )   echo -e " \
                            \n\
    -n | --niceness       nicesness of the sub-processes (default: +5)\n\
    -p | --project        set the project subfolder that should be synchronized\n\
         --source         the location of the source folder on the remote machine\n\
         --dest           the location of the destination folder on the local machine\n\
    -q | --quiet          don't print configuration info and file list\n\
    -d | --debug          print additional debug info\n\
         --config         an alternative configuration file to source instead of kconfig.sh\n\
                          (set to 'NONE' to inherit settings from parent environment)\n\
         --data-root      root folder for data repository\n\
         --yaml           also update YAML configuration files\n\
         --overwrite      download new copy of all files (not just update)\n\
    -h | --help           print this help \n\
                             "; exit 0;; # \n\ == 'line break, next line'; for syntax highlighting
    -- ) shift; break;; # this terminates the argument list, if GNU getopt is used
    * ) break;;
  esac # case $@
done # while getopts  

## load custom configuration from file
# N.B.: defaults and command line options will be overwritten by custom settings in config file
[ $VERBOSITY -gt 0 ] && echo
if [[ "$KCFG" == "NONE" ]]; then
    [ $VERBOSITY -gt 0 ] && echo "Using configuration from parent environment (not sourcing)."
elif [[ -z "$KCFG" ]]; then
    [ $VERBOSITY -gt 0 ] && echo "Sourcing configuration from default file: $PWD/hgsconfig.sh"
    source hgsconfig.sh # default config file (in local directory)
elif [[ -f "$KCFG" ]]; then 
    [ $VERBOSITY -gt 0 ] && echo "Sourcing configuration from alternative file: $KCFG"
    source "$KCFG" # alternative config file
else
    [ $VERBOSITY -gt 0 ] && echo "ERROR: no configuration file '$KCFG'"
fi # if config file
export KCFG='NONE' # suppress sourcing in child processes
[ $VERBOSITY -gt 0 ] && echo

# apply settings
SRC="${SRC:-"${DATA_ROOT}/HGS/${PROJECT}/"}" # local folder
DST="${DST:-"${HOST_ROOT}/HGS/${PROJECT}/"}" # remote folder

# assemble options
ROPT=${ROPT:-'--archive --compress'}
if [ $VERBOSITY -gt 0 ]; then ROPT="${ROPT} --verbose"; fi
if [[ "$OVERWRITE" == 'OVERWRITE' ]]; then ROPT="${ROPT} --ignore-times"; fi
if [[ -n "$YAML" ]]; then YINC="--include"; fi # need to define command as well

# print configuration for debug mode
[ $VERBOSITY -gt 0 ] && echo "Source folder: ${SRC}" && echo
if [ $VERBOSITY -gt 1 ]; then
  echo nice --adjustment=${NICENESS} rsync --links ${ROPT} ${YINC} ${YAML}
  echo "${SRC}" "${HOST}:${DST}"
  echo
fi # DEBUG

## execute rsync command
nice --adjustment=${NICENESS} rsync --links ${ROPT} ${YINC} ${YAML} \
      --include '*/' --include '*.asc'  --exclude '*' --prune-empty-dirs \
      "${SRC}" "${HOST}:${DST}" # remote and local host/folders
ERR=$?
# N.B.: this synchronizes all the hydrograph files, but also configuration and log files,
#       including the YAML configuration files and logs of the driver script

[ $VERBOSITY -gt 0 ] && echo && echo "Destination folder: ${DST}"

# report
if [ $VERBOSITY -gt 0 ]
  then
    echo; echo
    if [ $ERR -eq 0 ]
      then    echo "   <<<   Transfers Completed Successfully!   >>>   "
      else    echo "   ###   Transfers did not Complete! - Exit Code ${ERR}   ###   "
    fi
    echo
fi # VERBOSITY
exit $ERR