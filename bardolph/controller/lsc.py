#!/usr/bin/env python

import argparse
import os
import stat

from bardolph.controller import arg_helper, config_values
from bardolph.lib import injection, settings
from bardolph.parser.parse import Parser
from bardolph.runtime import runtime_module


def program_code(instructions):
    output = ''
    dot = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dot, 'lsc_template.py')) as srce:
        for line in srce:
            if line.find('#instructions') > -1:
                output += instructions
            else:
                output += line
    return output

def instruction_text(file_name):
    parser = Parser()
    if not parser.parse_file(file_name):
        print("Error compiling {}".format(file_name))
        print(parser.get_errors())
        return None

    program = parser.get_program()
    text = '    '
    text += ',\n    '.join(map(lambda inst: inst.as_list_text(), program))
    return text

def output_python(output_text, output_name=None):
    if output_name is None:
        print(output_text)
    else:
        out_file = open(output_name, 'w')
        out_file.write(output_text)
        out_file.close()
        os.chmod(output_name, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='name of the script file')
    arg_helper.add_o_argument(parser)
    args = parser.parse_args()

    injection.configure()
    settings.using(config_values.functional).apply_env().configure()
    runtime_module.configure()

    input_file = args.file
    program = instruction_text(input_file)
    if program is not None:
        output_python(program_code(program), arg_helper.get_output_file(args))

if __name__ == '__main__':
    main()
