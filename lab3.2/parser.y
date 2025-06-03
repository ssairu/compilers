%{
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "lexer.h"

char* indent(char* str, int level) {
    if (!str) return strdup("");
    char indent_str[10];
    sprintf(indent_str, "%*s", level * 2, "");
    char* result = malloc(10000);
    result[0] = '\0';
    char* line = strtok(str, "\n");
    if (line != NULL) {
        strcat(result, indent_str);
        strcat(result, line);
        line = strtok(NULL, "\n");
        while (line != NULL) {
            strcat(result, "\n");
            strcat(result, indent_str);
            strcat(result, line);
            line = strtok(NULL, "\n");
        }
    }
    return result;
}
%}

%define api.pure
%locations

%lex-param {yyscan_t scanner}
%parse-param {yyscan_t scanner}

%union {
    char* str;
}

%token TYPE FUN WHERE WEND COLON PIPE ARROW LBRACK RBRACK LPAREN RPAREN UNDERSCORE DOT
%token <str> ID NUMBER

%type <str> program decl_list decl type_decl constructor_list id_list fun_arg fun_body_list
%type <str> fun_decl fun_body pattern pattern_list expr expr_list local_defs

%start program

%%

program:
      decl_list { printf("%s\n", $1); }
    ;

decl_list:
      /* empty */ { $$ = ""; }
    | decl_list decl { $$ = malloc(10000); sprintf($$, "%s\n%s\n", $1, $2); }
    ;

decl:
      type_decl { $$ = $1; }
    | fun_decl { $$ = $1; }
    ;

type_decl:
      TYPE ID COLON constructor_list DOT { 
        char* indented = indent($4, 1); 
        $$ = malloc(10000); 
        sprintf($$, "type %s:\n%s.", $2, indented); 
        free(indented); 
      }
    ;

constructor_list:
      id_list { $$ = $1; }
    | id_list PIPE constructor_list { $$ = malloc(10000); sprintf($$, "%s |\n%s", $1, $3); }
    ;

id_list:
      ID { $$ = $1; } 
    | ID id_list { $$ = malloc(10000); sprintf($$, "%s %s", $1, $2); }
    ;

fun_decl:
      FUN LPAREN ID id_list RPAREN ARROW ID COLON fun_body_list DOT { 
        char* indented = indent($9, 1); 
        $$ = malloc(10000); 
        sprintf($$, "fun (%s %s) -> %s:\n%s.", $3, $4, $7, indented); 
        free(indented); 
      }
    ;

fun_body_list:
      fun_body { $$ = $1; }
    | fun_body PIPE fun_body_list { $$ = malloc(10000); sprintf($$, "%s |\n%s", $1, $3); }


fun_body:
      pattern ARROW expr_list { $$ = malloc(10000); sprintf($$, "%s -> %s", $1, $3); }
    | pattern ARROW expr_list WHERE local_defs WEND {
        char* indented = indent($5, 1); 
        $$ = malloc(10000); 
        sprintf($$, "%s -> %s\nwhere\n%s\nwend", $1, $3, indented); 
        free(indented); 
      }
    ;

pattern:
      fun_arg { $$ = $1; }
    | LBRACK pattern_list RBRACK { $$ = malloc(10000); sprintf($$, "[%s]", $2); }
    | LPAREN pattern_list RPAREN { $$ = malloc(10000); sprintf($$, "(%s)", $2); }
    ;
    
fun_arg:
      ID { $$ = $1; } 
    | NUMBER { $$ = $1; }
    | UNDERSCORE { $$ = "_"; }
    ;


pattern_list:
      pattern { $$ = $1; }
    | pattern pattern_list { $$ = malloc(10000); sprintf($$, "%s %s", $1, $2); }
    ;

expr:
      ID { $$ = $1; }
    | NUMBER { $$ = $1; }
    | LBRACK expr_list RBRACK { $$ = malloc(10000); sprintf($$, "[%s]", $2); }
    | LPAREN expr_list RPAREN { $$ = malloc(10000); sprintf($$, "(%s)", $2); }
    ;

expr_list:
      expr { $$ = $1; }
    | expr expr_list { $$ = malloc(10000); sprintf($$, "%s %s", $1, $2); }
    ;

local_defs:
      fun_decl { $$ = $1; }
    | fun_decl local_defs { $$ = malloc(10000); sprintf($$, "%s\n%s", $1, $2); }
    ;

%%

int main(int argc, char *argv[]) {
    FILE *input = stdin;
    yyscan_t scanner;
    struct Extra extra;

    if (argc > 1) {
        input = fopen(argv[1], "r");
        if (!input) {
            perror("fopen");
            return 1;
        }
    }

    init_scanner(input, &scanner, &extra);
    yyparse(scanner);
    destroy_scanner(scanner);

    if (input != stdin) {
        fclose(input);
    }

    return 0;
}
