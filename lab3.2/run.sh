#!/bin/bash

flex lexer.l
bison -d -Wcounterexamples parser.y
gcc -o formatter lex.yy.c parser.tab.c -lfl
rm -f lex.yy.c parser.tab.c parser.tab.h
./formatter input.txt > output.txt
