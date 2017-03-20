#!/usr/local/bin/python

import re
import sh
import sys
from subprocess import call

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
        matches = re.findall('(private|protected|public) \w* \w*\([^(^)^{^}]*\).*{',s)
        number_of_methods = len(matches)
    return number_of_methods

def get_number_of_protected_public_methods(file_name):
    number_of_methods = 0
    with open(file_name, 'r') as f:
        s = f.read()
        matches = re.findall('(protected|public) \w* \w*\([^(^)^{^}]*\).*{',s)
        number_of_methods = len(matches)
    return number_of_methods

def get_number_of_overriden_methods(file_name):
    number_of_overriden_methods = 0
    with open(file_name, 'r') as f:
        s = f.read()
        matches = re.findall('\@Override',s)
        number_of_overriden_methods = len(matches)
    return number_of_overriden_methods


sh.python("metrixplusplus-1.3.168/metrix++.py", "collect", "--std.code.lines.code", "--std.code.complexity.cyclomatic", "--std.code.lines.comments", file_name)
temp = sh.python("metrixplusplus-1.3.168/metrix++.py", "view")
average = re.findall('Average.*',str(temp))
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
    inherited_methods = get_inherited_methods(base_file)
    nr = get_number_of_protected_public_methods(file_name) - get_number_of_overriden_methods(file_name)
    return inherited_methods/float(inherited_methods+(nr))



# with open(file_name, 'r') as f:
#     s = f.read()
#     #matches = re.findall('\w* \w* \w*\([^(^)^{^}]*\).*{.*}',"".join(s.splitlines()))
#     #matches = re.findall('*(\s*)public \w* \w* \(.*\).*(?:\n\1  .*)*\n\1\}',s)
#     matches = re.findall('^(\s*)public.*\w*\w*\(.*\) \{\n\{\n((\t.*\n)|(^$\n))*^(\s*)\}',s)
#     print(matches)

# average_complexity = get_float(average[0])
# total_complexity = get_float(total[0])
# average_lines = get_float(average[1])
# total_lines = get_float(total[1])
# average_comments = get_float(average[2])
# total_comments = get_float(total[2])

# print("Number of methods: " + str(number_of_methods))
# print("# overriden methods: " + str(number_of_overriden_methods))
# print("Efferent coupling: " + str(effCoupling))
# print("Afferent coupling: " + str(affCoupling))
# print("Coupling: " + str(affCoupling + effCoupling))
# print("Subclasses: " + str(subclasses))
# print("Depth of inheritance tree, android code base so it is wrong..: " + str(get_depth_of_inheritance_tree_local(file_name)))
# print("MFA: " + str(get_MFA(file_name)))

def get_column(s):
    return str(s) + '\t'

print(get_column(total_lines) +
      get_column(number_of_methods) +
      get_column(number_of_overriden_methods) +
      get_column(total_comments) +
      get_column(total_lines/number_of_methods) +
      get_column(total_comments/(total_comments+total_lines)) +
      get_column("rfc") +
      get_column(affCoupling) +
      get_column(effCoupling) +
      get_column(affCoupling + effCoupling) +
      get_column("DIT") +
      get_column("LCOM") +
      get_column("MFA: " + str(get_MFA(file_name))) +
      get_column("NBD") +
      get_column(number_of_overriden_methods/number_of_methods) +
      get_column("NSC"))
