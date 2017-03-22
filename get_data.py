#!/usr/local/bin/python

import re
import sh
import sys

if len(sys.argv) >= 4:
    code_path = sys.argv[1]
    class_name = sys.argv[3]
    file_name = code_path + '/' + sys.argv[2] + '/' + class_name + '.java'
else:
    print("Usage examples: \n./android-static-analyzer/get_data.py <CODE-PATH> <PATH-TO-FILE> <FILE> ")
    exit(1)

matching_import1 = 'import.*\com.sfanytime.*\;'
matching_import2 = 'import.*\com.valtech.*\;'


def get_float(s):
    return float(s.split(':')[1])


def get_number_of_methods(file_name):
    number_of_methods = 0
    with open(file_name, 'r') as f:
        s = f.read()
        method_regex = '(?: )+?(?:public|private|protected)( | \w* )\w* \w*\([^(^)^{^}]*\).*{'
        matches = re.findall(method_regex,s)
        number_of_methods = len(matches)
    return number_of_methods


def get_number_of_protected_public_methods(file_name):
    number_of_methods = 0
    with open(file_name, 'r') as f:
        s = f.read()
        method_regex = '(?: )+?(?:public|protected)( | \w* )\w* \w*\([^(^)^{^}]*\).*{'
        matches = re.findall(method_regex,s)
        number_of_methods = len(matches)
    return number_of_methods


def get_number_of_overriden_methods(file_name):
    number_of_overriden_methods = 0
    with open(file_name, 'r') as f:
        s = f.read()
        matches = re.findall('\@Override',s)
        number_of_overriden_methods = len(matches)
    return number_of_overriden_methods


sh.python("../../metrixplusplus-1.3.168/metrix++.py", "collect", "--std.code.lines.code", "--std.code.complexity.cyclomatic", "--std.code.lines.comments", file_name)
temp = sh.python("../../metrixplusplus-1.3.168/metrix++.py", "view")
average = re.findall('Average.*', str(temp))
total = re.findall('Total.*', str(temp))

average_complexity = get_float(average[0])
total_complexity = get_float(total[0])
average_lines = get_float(average[1])
total_lines = get_float(total[1])
average_comments = get_float(average[2])
total_comments = get_float(total[2])

number_of_methods = get_number_of_methods(file_name)
number_of_overriden_methods = get_number_of_overriden_methods(file_name)


effCoupling = 0
with open(file_name, 'r') as f:
    s = f.read()
    matches = re.findall(matching_import1, s)
    matches_valtech = re.findall(matching_import2, s)
    effCoupling = len(matches + matches_valtech)

import_regexp = "import.*\." + class_name + ";"
matches = sh.grep("-r", import_regexp, code_path).splitlines()
affCoupling = len(matches)


extends_regexp = "extends " + class_name + " "
try:
    matches = sh.grep("-r", extends_regexp, code_path).splitlines()
    subclasses = len(matches)
except sh.ErrorReturnCode_1: 
    subclasses = 0


def get_base_class(file_name):
    with open(file_name, 'r') as f:
        s = f.read()
        extends_regexp = "extends \w* "
        matches = re.findall(extends_regexp, s)
        baseClass = matches[0].split(" ")[1]
        baseFile = sh.find(code_path, "-name", baseClass + ".java")
        try:
            fileString = baseFile.splitlines()[-1]
            return fileString
        except IndexError:
            return ""


def get_depth_of_inheritance_tree_local(file_name):
    base_file = get_base_class(file_name)
    if base_file == "":
        return 0
    else:
        return 1 + get_depth_of_inheritance_tree_local(base_file)


def get_inherited_methods(file_name):
    base_file = get_base_class(file_name)
    nr = get_number_of_protected_public_methods(file_name) - get_number_of_overriden_methods(file_name)
    if base_file == "":
        return nr
    else:
        return nr + get_inherited_methods(base_file)


def get_MFA(file_name):
    base_file = get_base_class(file_name)
    if base_file == "":
        return 0
    inherited_methods = get_inherited_methods(base_file)
    nr = get_number_of_protected_public_methods(file_name) - get_number_of_overriden_methods(file_name)
    if inherited_methods==0:
        return 0
    else:
        return inherited_methods/float(inherited_methods+(nr))


########
# Get nesting
########

def update_max_nesting(curr, max):
    if (curr > max):
        return curr
    return max


def update_nesting(line, curr):
    opening_brace_regex = '{'
    closing_brace_regex = '}'
    opening = re.findall(opening_brace_regex, line)
    closing = re.findall(closing_brace_regex, line)
    return curr + len(opening) - len(closing)


def get_nesting_level(file_name):
    flist = open(file_name).readlines()
    method_regex = '(if|for|while|else|switch).*\('
    parsing = False
    current_nesting_depth = 0
    max_nesting_depth = 0
    for line in flist:
        match = re.findall(method_regex, line);
        if match:
            parsing = True
        if parsing:
            current_nesting_depth = update_nesting(line, current_nesting_depth)
            max_nesting_depth = update_max_nesting(current_nesting_depth, max_nesting_depth)
            if (current_nesting_depth == 0):
                parsing = False
    return max_nesting_depth


########
# Get LCOM
########

def get_method_strings(file_name):
    flist = open(file_name).readlines()
    method_regex = '^( )*?(?:public|private|protected)( | \w* )\w* \w*\([^(^)^{^}]*\).*{'

    in_function = False
    current_nesting_depth = 0
    function_list = []
    start_row = 0
    for idx, line in enumerate(flist):
        match = re.findall(method_regex, line)
        if match:
            in_function = True
            start_row = idx
        if in_function:
            current_nesting_depth = update_nesting(line, current_nesting_depth)
            if (current_nesting_depth == 0):
                function_rows = flist[start_row:idx+1]
                function = "".join(function_rows)
                function_list.append(function)
                in_function = False
    return function_list


def get_code_before_first_function_inside_class(file_name):
    flist = open(file_name).readlines()
    class_regex = 'public class '
    method_regex = '^( )*?(?:public|private|protected)( | \w* )\w* \w*\([^(^)^{^}]*\).*{'
    class_idx = 0
    for idx, line in enumerate(flist):
        match_class = re.findall(class_regex, line)
        match_method = re.findall(method_regex, line)
        if match_class:
            class_idx = idx
        if match_method:
            return flist[class_idx+1:idx]


def get_attribute_from_row(row):
    r = row.strip().split(" ")
    if len(r) == 2:
        return r[1]
    elif len(r) == 3 and r[0] == 'private':
        return r[2]
    elif len(r) >= 4 and r[-3] == '=':
        return r[-4]
    elif len(r) >= 3 and r[-2] == '=':
        return r[-3]
    elif len(r) >= 2 and r[-1] == '=':
        return r[-2]

    else:
        return "..."


def is_whitespace(x):
    if x.isspace() or x == '':
        return False
    else:
        return True

def get_class_attributes(file_name):
    code_list = get_code_before_first_function_inside_class(file_name)
    code_string = "".join(code_list)
    m = filter(is_whitespace, re.findall('(?:private|public|protected|\w*) (?: |\w|\<|\>|\=)*', code_string))
    attributes = map(get_attribute_from_row, m)
    return attributes


def get_sum_of_attributes_in_methods(file_name):
    method_list = get_method_strings(file_name)
    attribute_list = get_class_attributes(file_name)
    sum = 0
    for attribute in attribute_list:
        for method in method_list:
            if re.search(attribute, method):
                sum += 1
    return sum


def get_LCOM(file_name):
    a_sum = get_sum_of_attributes_in_methods(file_name)
    nr_attributes = len(get_class_attributes(file_name))
    return float((a_sum/nr_attributes)-number_of_methods)/float(1-number_of_methods)


#######
# Get RFC
#######


def get_rfc(file_name):
    number_of_methods = 0
    with open(file_name, 'r') as f:
        s = f.read()
        m = re.findall('(?:public|private|protected) \w* \w*\([^(^)^{^}]*\).*{',s)
        methods = map(lambda x: re.findall('\w*\(',x)[0], m)
        numbers = map(lambda x: sh.grep(" " + x,file_name,'-c'), methods)
        count = reduce(lambda x, y: int(x) + int(y), numbers)
        rfc = count-len(m)
    return rfc


#######
# Get remaining variables
#######

rfc = get_rfc(file_name)
depth_of_inheritance = get_depth_of_inheritance_tree_local(file_name)
lcom = get_LCOM(file_name)
mfa = get_MFA(file_name)
nesting_level = get_nesting_level(file_name)


#######
# Print result
#######
def get_column(s):
    return "{:0.2f}\t".format(s)

print(get_column(total_lines) +
      get_column(number_of_methods) +
      get_column(number_of_overriden_methods) +
      get_column(total_comments) +
      get_column(total_lines/number_of_methods) +
      get_column(total_comments/(total_comments+total_lines)) +
      get_column(rfc) +
      get_column(affCoupling) +
      get_column(effCoupling) +
      get_column(affCoupling + effCoupling) +
      #See if there are any changes and update accordingly
      get_column(depth_of_inheritance) +
      get_column(lcom) +
      get_column(mfa) +
      get_column(nesting_level) +
      get_column(number_of_overriden_methods/number_of_methods) +
      get_column(subclasses))
