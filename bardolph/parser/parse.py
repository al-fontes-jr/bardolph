#!/usr/bin/env python

import argparse
import logging
import re

from ..controller.instruction import Instruction, OpCode, Operand
from ..controller.instruction import Register, TimePatternOp
from ..controller.units import UnitMode, Units
from . import lex
from ..lib.time_pattern import TimePattern
from .token_types import TokenTypes


WORD_REGEX = re.compile(r"\w+")


class Parser:
    def __init__(self):
        self._lexer = None
        self._error_output = ''
        self._light_state = {}
        self._name = None
        self._current_token_type = None
        self._current_token = None
        self._op_code = OpCode.NOP
        self._symbol_table = {}
        self._code = []
        self._unit_mode = UnitMode.LOGICAL

    def parse(self, input_string):
        self._code.clear()
        self._error_output = ''
        self._lexer = lex.Lex(input_string)
        self._next_token()
        success = self._script()
        self._lexer = None
        if not success:
            return None
        self._optimize()
        return self._code

    def load(self, file_name):
        logging.debug('File name: {}'.format(file_name))
        try:
            srce = open(file_name, 'r')
            input_string = srce.read()
            srce.close()
            return self.parse(input_string)
        except FileNotFoundError:
            logging.error('Error: file {} not found.'.format(file_name))
        except OSError:
            logging.error('Error accessing file {}'.format(file_name))

    def get_errors(self):
        return self._error_output

    def _script(self):
        return self._body() and self._eof()

    def _body(self):
        succeeded = True
        while succeeded and self._current_token_type != TokenTypes.EOF:
            succeeded = self._command()
        return succeeded

    def _eof(self):
        if self._current_token_type != TokenTypes.EOF:
            return self._trigger_error("Didn't get to end of file.")
        return True

    def _command(self):
        return {
            TokenTypes.DEFINE: self._definition,
            TokenTypes.GET: self._get,
            TokenTypes.OFF: self._power_off,
            TokenTypes.ON: self._power_on,
            TokenTypes.PAUSE: self._pause,
            TokenTypes.REGISTER: self._set_reg,
            TokenTypes.SET: self._set,
            TokenTypes.UNITS: self._set_units,
        }.get(self._current_token_type, self._syntax_error)()

    def _set_reg(self):
        self._name = self._current_token
        if Register.TIME.name.lower() == self._name:
            return self._time()
                
        self._next_token()
        if self._current_token_type == TokenTypes.NUMBER:
            try:
                value = round(float(self._current_token))
            except ValueError:
                return self._token_error('Invalid number: "{}"')
        elif self._current_token_type == TokenTypes.LITERAL:
            value = self._current_token
        elif self._current_token in self._symbol_table:
            value = self._symbol_table[self._current_token]
        else:
            return self._token_error('Unknown parameter value: "{}"')
        
        self._add_reg_instruction(self._name, value)
        return self._next_token()

    def _add_reg_instruction(self, name, value):
        reg_name = Register[name.upper()]
        units = Units()
        if self._unit_mode == UnitMode.LOGICAL:
            value = units.as_raw(reg_name, value)
            if units.has_range(reg_name):
                (min_val, max_val) = units.get_range(reg_name)
                if value < min_val or value > max_val:
                    if self._unit_mode == UnitMode.LOGICAL:
                        min_val = units.as_logical(reg_name, min_val)
                        max_val = units.as_logical(reg_name, max_val)
                    return self._trigger_error(
                        '{} must be between {} and {}'.format(
                            reg_name.lower(), min_val, max_val))
        self._add_instruction(OpCode.SET_REG, reg_name, value)

    def _set_units(self):
        self._next_token()
        mode = {
            TokenTypes.RAW: UnitMode.RAW,
            TokenTypes.LOGICAL:UnitMode.LOGICAL
        }.get(self._current_token_type, None)

        if mode is None:
            return self._trigger_error(
                'Invalid parameter "{}" for units.'.format(self._current_token))

        self._unit_mode = mode
        return self._next_token()

    def _set(self):
        return self._action(OpCode.COLOR)

    def _get(self):
        return self._action(OpCode.GET_COLOR)

    def _power_on(self):
        self._add_instruction(OpCode.SET_REG, Register.POWER, True)
        return self._action(OpCode.POWER)

    def _power_off(self):
        self._add_instruction(OpCode.SET_REG, Register.POWER, False)
        return self._action(OpCode.POWER)

    def _pause(self):
        self._add_instruction(OpCode.PAUSE)
        self._next_token()
        return True
    
    def _time(self):
        name = self._current_token
        self._next_token()
        
        if self._current_token_type == TokenTypes.AT:
            return self._process_time_patterns()
        if self._current_token_type == TokenTypes.NUMBER:
            self._add_reg_instruction(name, int(self._current_token))
            return self._next_token()
        
        return self._time_spec_error()
    
    def _process_time_patterns(self):
        self._next_token()
        if self._current_token_type != TokenTypes.TIME_PATTERN:
            return self.time_spec_error()  

        if not self._time_pattern_inst(TimePatternOp.INIT):
            return False
        
        self._next_token()
        while self._current_token_type == TokenTypes.OR:
            self._next_token()
            if self._current_token_type != TokenTypes.TIME_PATTERN:
                return self.time_spec_error()
            if not self._time_pattern_inst(TimePatternOp.UNION):
                return False
            self._next_token()

        return True;
    
    def _time_pattern_inst(self, time_pattern_op):
        pattern = TimePattern.from_string(self._current_token)
        if pattern is None:
            return self._token_error("Invalid time pattern: {}")
        self._add_instruction(OpCode.TIME_PATTERN, time_pattern_op, pattern)
        return True

    def _action(self, op_code):
        self._op_code = op_code
        self._next_token()

        if self._current_token_type == TokenTypes.GROUP:
            self._add_instruction(
                OpCode.SET_REG, Register.OPERAND, Operand.GROUP)
            self._next_token()
        elif self._current_token_type == TokenTypes.LOCATION:
            self._add_instruction(
                OpCode.SET_REG, Register.OPERAND, Operand.LOCATION)
            self._next_token()
        elif self._current_token_type != TokenTypes.ALL:
            self._add_instruction(
                OpCode.SET_REG, Register.OPERAND, Operand.LIGHT)

        return self._operand_list()

    def _operand_list(self):
        if self._current_token_type == TokenTypes.ALL:
            self._add_instruction(OpCode.SET_REG, Register.NAME, None)
            self._add_instruction(
                OpCode.SET_REG, Register.OPERAND, Operand.ALL)
            if self._op_code != OpCode.GET_COLOR:
                self._add_instruction(OpCode.TIME_WAIT)
            self._add_instruction(self._op_code)
            return self._next_token()

        if not self._operand_name():
            return False

        self._add_instruction(OpCode.SET_REG, Register.NAME, self._name)
        if self._op_code != OpCode.GET_COLOR:
            self._add_instruction(OpCode.TIME_WAIT)
        self._add_instruction(self._op_code)
        while self._current_token_type == TokenTypes.AND:
            if not self._and():
                return False
        return True

    def _operand_name(self):
        if self._current_token_type == TokenTypes.LITERAL:
            self._name = self._current_token
        elif self._current_token in self._symbol_table:
            self._name = self._symbol_table[self._current_token]
        else:
            return self._token_error('Unknown variable: {}')
        return self._next_token()

    def _and(self):
        self._next_token()
        if not self._operand_name():
            return False
        self._add_instruction(OpCode.SET_REG, Register.NAME, self._name)
        self._add_instruction(self._op_code)
        return True

    def _definition(self):
        self._next_token()
        if self._current_token_type in [
                TokenTypes.LITERAL, TokenTypes.NUMBER]:
            return self._token_error('Unexpected literal: {}')

        var_name = self._current_token
        self._next_token()
        if self._current_token_type == TokenTypes.NUMBER:
            value = int(self._current_token)
        elif self._current_token_type == TokenTypes.LITERAL:
            value = self._current_token
        elif self._current_token in self._symbol_table:
            value = self._symbol_table[self._current_token]
        else:
            return self._token_error('Unknown term: "{}"')

        self._symbol_table[var_name] = value
        self._next_token()
        return True

    def _add_instruction(self, op_code, param0=None, param1=None):
        self._code.append(Instruction(op_code, param0, param1))

    def _add_message(self, message):
        self._error_output += '{}\n'.format(message)

    def _trigger_error(self, message):
        full_message = 'Line {}: {}'.format(
            self._lexer.get_line_number(), message)
        logging.error(full_message)
        self._add_message(full_message)
        return False

    def _next_token(self):
        (self._current_token_type,
         self._current_token) = self._lexer.next_token()
        return True

    def _token_error(self, message_format):
        return self._trigger_error(message_format.format(self._current_token))

    def _syntax_error(self):
        return self._token_error('Unexpected input "{}"')

    def _time_spec_error(self):
        return self._token_error('Invalid time specification: {}')  

    def _optimize(self):
        """
        Eliminate SET_REG if it has the same value as the previous SET_REG
        instruction.
        
        For this instruction, param0 is the name of the register, and param1 is
        the value to which the register is set.

        Any GET_COLOR instruction clears out the previous value cache.
        """
        opt = []
        prev_value = {}
        for inst in self._code:
            if inst.op_code == OpCode.GET_COLOR:
                prev_value = {}
            if inst.op_code != OpCode.SET_REG:
                opt.append(inst)
            else:
                key = str(inst.param0)
                if key not in prev_value or prev_value[key] != inst.param1:
                    opt.append(inst)
                    prev_value[key] = inst.param1
        self._code = opt


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('file', help='name of the script file')
    args = arg_parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(filename)s(%(lineno)d) %(funcName)s(): %(message)s')
    parser = Parser()
    output_code = parser.load(args.file)
    if output_code:
        for inst in output_code:
            print(inst)
    else:
        print(parser.get_errors())


if __name__ == '__main__':
    main()

"""
    <script> ::= <body> <EOF>
    <body> ::= <command> *
    <command> ::=
        "brightness" <set_reg>
        | "define" <definition>
        | "duration" <set_reg>
        | "hue" <set_reg>
        | "kelvin" <set_reg>
        | "off" <power_off>
        | "on" <power_on>
        | "_pause" <pause>
        | "saturation" <set_reg>
        | "_set" <set>
        | "units" <set_units>
        | "time" <time_spec>
    <set_reg> ::= <name> <number> | <name> <literal> | <name> <symbol>
    <set> ::= <action>
    <set_units> ::= "logical" | "raw"
    <get> ::= <action>
    <power_off> ::= <action>
    <power_on> ::= <action>
    <time_spec> ::= <number> | <time_pattern_set>
    <time_pattern_set> ::= <time_pattern> | <time_pattern> "or" <time_pattern>
    <time_pattern> ::= <hour_pattern> ":" <minute_pattern>
    <hour_pattern> ::= <digit> | <digit><digit> | "*" <digit> |
                        <digit> "*" | "*"
    <minute_pattern> ::= <digit><digit> | <digit> "*" | "*" <digit> | "*"
    <action> ::= <op_code> <operand_list>
    <operand_list> ::= "all" | <operand_name> | <operand_name> <and> *
    <operand_name> ::= <token>
    <and> ::= "and" <operand_name>
    <definition> ::= <token> <number> | <token> <literal>
    <literal> ::= "\"" <token> "\""
"""
