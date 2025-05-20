@echo off
flex lexer.l
bison -d parser.y
gcc -o calc *.c
erase lex.yy.c parser.tab.?
calc.exe input.txt
