#!/bin/bash
set -ex
RUNDIR="$(cd "$(dirname "$0")" ; pwd -P)"
BUILDDIR="$RUNDIR/build"
VERB=
FILTER=
RMBUILD=1
LOGFILE=/tmp/pytorch_cpp_test.log

while getopts 'VLKF:' OPTION
do
  case $OPTION in
    V)
      VERB="VERBOSE=1"
      ;;
    L)
      LOGFILE=
      ;;
    K)
      RMBUILD=0
      ;;
    F)
      FILTER="--gtest_filter=$OPTARG"
      ;;
  esac
done
shift $(($OPTIND - 1))

rm -rf "$BUILDDIR"
mkdir "$BUILDDIR" 2>/dev/null
pushd "$BUILDDIR"
cmake "$RUNDIR" \
    -DPYTHON_INCLUDE_DIR=$(python -c "from distutils.sysconfig import get_python_inc; print(get_python_inc())")\
    -DPYTHON_LIBRARY=$(python -c "import distutils.sysconfig as sysconfig; print(sysconfig.get_config_var('LIBDIR') + '/' + sysconfig.get_config_var('LDLIBRARY'))")
make $VERB
if [ "$LOGFILE" != "" ]; then
  ./test_ptxla ${FILTER:+"$FILTER"} 2>$LOGFILE
else
  ./test_ptxla ${FILTER:+"$FILTER"}
fi
popd
if [ $RMBUILD -eq 1 ]; then
  rm -rf "$BUILDDIR"
fi
