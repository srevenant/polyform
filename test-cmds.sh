#!/bin/bash

tmp=_test-tmp
rm -rf $tmp &&\
  mkdir $tmp &&\
  cd $tmp &&\
  poly init testing &&\
#  poly build testing &&\
  poly codetest &&\
  poly sh testing echo hi


