#!/bin/bash

flex lexer.l
bison -d parser.y
gcc -o calc *.c
rm -f lex.yy.c parser.tab.?
./calc input.txt
