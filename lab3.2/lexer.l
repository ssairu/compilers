%option reentrant noyywrap bison-bridge bison-locations
%option extra-type="struct Extra *"

%{
#include <stdio.h>
#include <stdlib.h>
#include "lexer.h"
#include "parser.tab.h"

#define YY_USER_ACTION \
  { \
    int i; \
    struct Extra *extra = yyextra; \
    if (!extra->continued) { \
      yylloc->first_line = extra->cur_line; \
      yylloc->first_column = extra->cur_column; \
    } \
    extra->continued = false; \
    for (i = 0; i < yyleng; ++i) { \
      if (yytext[i] == '\n') { \
        extra->cur_line += 1; \
        extra->cur_column = 1; \
      } else { \
        extra->cur_column += 1; \
      } \
    } \
    yylloc->last_line = extra->cur_line; \
    yylloc->last_column = extra->cur_column; \
  }

void yyerror(YYLTYPE *loc, yyscan_t scanner, const char *message) {
    printf("Error (%d,%d): %s\n", loc->first_line, loc->first_column, message);
}
%}

%%

"type"      { return TYPE; }
"fun"       { return FUN; }
"where"     { return WHERE; }
"wend"      { return WEND; }
":"         { return COLON; }
"|"         { return PIPE; }
"->"        { return ARROW; }
"["         { return LBRACK; }
"]"         { return RBRACK; }
"("         { return LPAREN; }
")"         { return RPAREN; }
"_"         { return UNDERSCORE; }
"."         { return DOT; }
[a-zA-Z_][a-zA-Z0-9_]*  { yylval->str = strdup(yytext); return ID; }
[0-9]*      { yylval->str = strdup(yytext); return NUMBER; }
[ \t\n]+    /* ignore */
"<<".*">>"  /* comments */

%%

void init_scanner(FILE *input, yyscan_t *scanner, struct Extra *extra) {
    extra->continued = false;
    extra->cur_line = 1;
    extra->cur_column = 1;
    yylex_init(scanner);
    yylex_init_extra(extra, scanner);
    yyset_in(input, *scanner);
}

void destroy_scanner(yyscan_t scanner) {
    yylex_destroy(scanner);
}
