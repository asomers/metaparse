#!/usr/bin/python
"""Utility to generate the header files for BOOST_METAPARSE_STRING"""

# Copyright Abel Sinkovics (abel@sinkovics.hu) 2016.
# Distributed under the Boost Software License, Version 1.0.
#    (See accompanying file LICENSE_1_0.txt or copy at
#          http://www.boost.org/LICENSE_1_0.txt)

import argparse
import os
import re
import sys


VERSION = 1


class Namespace(object):
    """Generate namespace definition"""

    def __init__(self, out_f, names):
        self.out_f = out_f
        self.names = names

    def begin(self):
        """Generate the beginning part"""
        self.out_f.write('\n')
        for depth, name in enumerate(self.names):
            self.out_f.write(
                '{0}namespace {1}\n{0}{{\n'.format(self.prefix(depth), name)
            )

    def end(self):
        """Generate the closing part"""
        for depth in xrange(len(self.names) - 1, -1, -1):
            self.out_f.write('{0}}}\n'.format(self.prefix(depth)))

    def prefix(self, depth=None):
        """Returns the prefix of a given depth. Returns the prefix code inside
        the namespace should use when depth is None."""
        if depth is None:
            depth = len(self.names)
        return '  ' * depth

    def path(self):
        """Returns the full path of the namespace"""
        return '::' + '::'.join(self.names)

    def __enter__(self):
        self.begin()
        return self

    def __exit__(self, typ, value, traceback):
        self.end()


def write_autogen_info(out_f):
    """Write the comment about the file being autogenerated"""
    out_f.write(
        '\n'
        '// This is an automatically generated header file.\n'
        '// Generated with the tools/string_headers.py utility of\n'
        '// Boost.Metaparse\n'
    )


def write_no_include_guard_info(out_f):
    """Write a comment explaining why there are is include guard"""
    out_f.write(
        '// no include guard: the header might be included multiple times\n'
    )


class IncludeGuard(object):
    """Generate include guards"""

    def __init__(self, out_f, name, undefine=False):
        self.out_f = out_f
        if undefine:
            self.name = 'UNDEF_{0}'.format(name.upper())
        else:
            self.name = name.upper()

    def begin(self):
        """Generate the beginning part"""
        name = 'BOOST_METAPARSE_V1_IMPL_{0}_HPP'.format(self.name)
        self.out_f.write('#ifndef {0}\n#define {0}\n'.format(name))
        write_autogen_info(self.out_f)

    def end(self):
        """Generate the closing part"""
        self.out_f.write('\n#endif\n')

    def __enter__(self):
        self.begin()
        return self

    def __exit__(self, typ, value, traceback):
        self.end()


def macro_name(name):
    """Generate the full macro name"""
    return 'BOOST_METAPARSE_V{0}_{1}'.format(VERSION, name)


def define_macro(out_f, (name, args, body), undefine=False, check=True):
    """Generate a macro definition or undefinition"""
    if undefine:
        out_f.write(
            '#undef {0}\n'
            .format(macro_name(name))
        )
    else:
        if len(args) > 0:
            arg_list = '({0})'.format(', '.join(args))
        else:
            arg_list = ''

        if check:
            out_f.write(
                '#ifdef {0}\n'
                '#  error {0} already defined.\n'
                '#endif\n'
                .format(macro_name(name))
            )

        out_f.write(
            '#define {0}{1} {2}\n'.format(macro_name(name), arg_list, body)
        )


def filename(out_dir, name, undefine=False):
    """Generate the filename"""
    if undefine:
        prefix = 'undef_'
    else:
        prefix = ''
    return os.path.join(out_dir, '{0}{1}.hpp'.format(prefix, name.lower()))


def generate_enum(out_dir, name, internal_name, max_count, undefine):
    """Generate an enumeration macro"""
    cat = macro_name('CAT')
    with open(filename(out_dir, name, undefine), 'wb') as out_f:
        write_no_include_guard_info(out_f)
        write_autogen_info(out_f)

        define_macro(
            out_f,
            (
                name, ['count', 'param'],
                '{0}({1}, count)(param)'.format(cat, macro_name(internal_name))
            ),
            undefine
        )

        define_macro(
            out_f,
            ('{0}0'.format(internal_name), ['param'], ''),
            undefine,
            False
        )
        define_macro(
            out_f,
            (
                '{0}1'.format(internal_name), ['param'],
                '{0}(param, 0)'.format(cat)
            ),
            undefine,
            False
        )

        for count in xrange(2, max_count + 1):
            define_macro(
                out_f,
                (
                    '{0}{1}'.format(internal_name, count), ['param'],
                    '{0}{1}(param), {2}(param, {1})'
                    .format(macro_name(internal_name), count - 1, cat)
                ),
                undefine,
                False
            )


def generate_repetition(out_dir, name, internal_name, max_count, undefine):
    """Generate a repetition macro"""
    cat = macro_name('CAT')
    with open(filename(out_dir, name, undefine), 'wb') as out_f:
        write_no_include_guard_info(out_f)
        write_autogen_info(out_f)

        define_macro(
            out_f,
            (
                name, ['count', 'param'],
                '{0}({1}, count)(param)'.format(cat, macro_name(internal_name))
            ),
            undefine
        )

        define_macro(
            out_f,
            ('{0}0'.format(internal_name), ['param'], ''),
            undefine,
            False
        )
        define_macro(
            out_f,
            ('{0}1'.format(internal_name), ['param'], 'param'),
            undefine,
            False
        )

        for count in xrange(2, max_count + 1):
            define_macro(
                out_f,
                (
                    '{0}{1}'.format(internal_name, count), ['param'],
                    '{0}{1}(param), param'
                    .format(macro_name(internal_name), count - 1)
                ),
                undefine,
                False
            )


def length_limits(max_length_limit, length_limit_step):
    """Generates the length limits"""
    string_len = len(str(max_length_limit))
    return [
        str(i).zfill(string_len) for i in
        xrange(
            length_limit_step,
            max_length_limit + length_limit_step - 1,
            length_limit_step
        )
    ]


def generate_string_indexing(length_limit):
    """Generate the code for indexing a string literal"""
    left = length_limit
    result = []
    for exp in xrange(3, 0, -1):
        step, left = divmod(left, 16 ** exp)
        result = result + [
            'BOOST_METAPARSE_V1_STRING_AT{0}((s), {1:X})'.format(exp, i)
            for i in xrange(0, step)
        ]
    result = result + [
        '::boost::metaparse::v{0}::impl::string_at<{1}>((s), {2})'.format(
            VERSION,
            length_limit,
            i
        ) for i in xrange(0, left)
    ]
    return ', '.join(result)


def generate_with_length_limit(out_dir, length_limit_str):
    """Generate one string implementation"""
    length_limit = int(length_limit_str)
    name = 'string{0}'.format(length_limit_str)
    with open(filename(out_dir, name), 'wb') as out_f:
        with IncludeGuard(out_f, name):
            define_macro(out_f, ('TMP_LENGTH_LIMIT', [], str(length_limit)))
            with Namespace(
                out_f,
                ['boost', 'metaparse', 'v{0}'.format(VERSION), 'impl']
            ) as nsp:
                out_f.write('{0}{1}\n'.format(
                    nsp.prefix(),
                    macro_name('DEFINE_STRING')
                ))
                out_f.write('\n')
                for spec_length in xrange(1, length_limit):
                    out_f.write(
                        '{0}{1}({2}, {3})\n'
                        .format(
                            nsp.prefix(),
                            macro_name(''),
                            spec_length,
                            length_limit - spec_length
                        )
                    )
                out_f.write(
                    '{0}{1}\n'
                    .format(nsp.prefix(), macro_name('SPECIALISE_STRING0'))
                )
            define_macro(out_f, ('TMP_LENGTH_LIMIT', [], ''), True)

            define_macro(
                out_f,
                (
                    'STRING{0}'.format(length_limit),
                    ['s'],
                    '{0}::string{1}<{2}>::type'
                    .format(
                        nsp.path(),
                        length_limit,
                        generate_string_indexing(length_limit)
                    )
                )
            )


def max_value(values):
    """Converts the values to int and returns the maximum value"""
    return max((int(v) for v in values))


def generate_headers(out_dir, limits):
    """Generate all header files"""
    max_limit = max_value(limits)
    for undefine in [True, False]:
        generate_enum(out_dir, 'ENUM_PARAMS', 'EP', max_limit, undefine)
        generate_repetition(
            out_dir,
            'ENUM_CONSTANT', 'EC',
            max_limit,
            undefine
        )

    for length_limit in limits:
        generate_with_length_limit(out_dir, length_limit)


def generate_string(out_dir, limits):
    """Generate string.hpp"""
    with open(filename(out_dir, 'string'), 'wb') as out_f:
        write_no_include_guard_info(out_f)
        write_autogen_info(out_f)

        headers = [
            'enum_params',
            'cat',
            'enum_constant',
            'define_string',
            'specialise_string'
        ]

        out_f.write(
            '\n'
            '#ifndef BOOST_METAPARSE_LIMIT_STRING_SIZE\n'
            '#  error BOOST_METAPARSE_LIMIT_STRING_SIZE not defined\n'
            '#endif\n'
        )

        out_f.write(
            '\n'
            '#ifdef BOOST_METAPARSE_V1_STRING\n'
            '#  undef BOOST_METAPARSE_V1_STRING\n'
            '#endif\n'
            '\n'
        )

        for header in headers:
            out_f.write(
                '#include <boost/metaparse/v{0}/impl/{1}.hpp>\n'
                .format(VERSION, header)
            )

        out_f.write('\n')

        for nth, length_limit in enumerate(limits):
            if_name = '#if' if nth == 0 else '#elif'

            out_f.write(
                '{0} BOOST_METAPARSE_LIMIT_STRING_SIZE <= {1}\n'
                '#  include <boost/metaparse/v{2}/impl/string{3}.hpp>\n'
                '#  define BOOST_METAPARSE_V1_STRING'
                ' BOOST_METAPARSE_V1_STRING{1}\n'
                .format(if_name, int(length_limit), VERSION, length_limit)
            )

        out_f.write(
            '#else\n'
            '#  error BOOST_METAPARSE_LIMIT_STRING_SIZE is greater than {0}.'
            ' To increase the limit run tools/string_headers.py of'
            ' Boost.Metaparse against your Boost headers.\n'
            '#endif\n'
            '\n'
            .format(max_value(limits))
        )

        for header in headers:
            out_f.write(
                '#include <boost/metaparse/v{0}/impl/undef_{1}.hpp>\n'
                .format(VERSION, header)
            )


def remove_file(path, fname):
    """Delete the file if exists"""
    try:
        os.remove(os.path.join(path, fname))
    except OSError:
        pass


def remove_old_headers(out_dir):
    """Delete previously generated header files"""
    for prefix in ['', 'undef_']:
        remove_file(out_dir, '{0}enum_params.hpp'.format(prefix))
        remove_file(out_dir, '{0}enum_constant.hpp'.format(prefix))
        remove_file(out_dir, '{0}string.hpp'.format(prefix))

    string_header = re.compile('string[0-9]+.hpp')
    for header in os.listdir(out_dir):
        if string_header.match(header):
            remove_file(out_dir, header)


def generate(out_dir, limits):
    """Do the header cleanup and generation"""
    remove_old_headers(out_dir)
    generate_string(out_dir, limits)
    generate_headers(out_dir, limits)


def positive_integer(value):
    """Throws when the argument is not a positive integer"""
    val = int(value)
    if val > 0:
        return val
    else:
        raise argparse.ArgumentTypeError("A positive number is expected")


def existing_path(value):
    """Throws when the path does not exist"""
    if not os.path.exists(value):
        raise argparse.ArgumentTypeError("Path {0} not found".format(value))


def main():
    """The main function of the script"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--boost_dir',
        required=False,
        type=existing_path,
        help='The path to the include/boost directory of Metaparse'
    )
    parser.add_argument(
        '--max_length_limit',
        required=False,
        default=2048,
        type=positive_integer,
        help='The maximum supported length limit'
    )
    parser.add_argument(
        '--length_limit_step',
        required=False,
        default=128,
        type=positive_integer,
        help='The longest step at which headers are generated'
    )
    args = parser.parse_args()

    if args.boost_dir is None:
        tools_path = os.path.dirname(os.path.abspath(__file__))
        boost_dir = os.path.join(
            os.path.dirname(tools_path),
            'include',
            'boost'
        )
    else:
        boost_dir = args.boost_dir

    if args.max_length_limit < 1:
        sys.stderr.write('Invalid maximum length limit')
        sys.exit(-1)

    generate(
        os.path.join(boost_dir, 'metaparse', 'v{0}'.format(VERSION), 'impl'),
        length_limits(args.max_length_limit, args.length_limit_step)
    )


if __name__ == '__main__':
    main()
