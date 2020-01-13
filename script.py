import fnmatch
import getopt
import os
import subprocess
import sys
from typing import List, TextIO, Dict

import htmlgen

from utils import *


def main(argv):
    # name of package (read from command line)
    package: str = ""

    # tools to use (read from command line)
    tools: Set[str] = set()

    # path of auxiliary classpath file
    aux_classpath_from_file_path: str = ""

    # booleans implying the use of tools that require -c (classpath argument) and -p (package argument)
    c_tool: bool = False
    p_tool: bool = False

    # boolean, tells us if the last argument in command line is a directory of a normal Java file
    directory: bool = True

    # last argument, path of Android Studio project or a single Java file
    project_path: str = ""

    # project_path + "app/src"
    project_path_appsrc: str = ""

    # project_path_appsrc + package
    project_path_package: str = ""

    # scores of tools, as calculated by calculate_score methods
    scores: Dict[str, int] = {}

    try:
        opts, args = getopt.getopt(argv, "hlt:c:p:")
    except getopt.GetoptError:
        print(getopt.GetoptError.msg + "Incorrect arguments."
                                       "\nFor help read README file or run the script with -h option")
        sys.exit(1)

    # check passed arguments, read them and set up necessary variables (c_tool, p_tool...)
    for opt, arg in opts:
        if opt == HELP_ARG:
            if len(opts) != 1:
                print("Incorrect arguments.\nFor help read README file or run the script with -h option")
            print(HELP)
            sys.exit(1)
        elif opt == LIST_ARG:
            if len(opts) != 1:
                print("Incorrect arguments.\nFor help read README file or run the script with -h option")
                sys.exit(1)
            print("Available tools are:")
            print(*ALL_TOOLS, sep=",")
            sys.exit(1)
        elif opt == TOOLS_ARG:
            tools = arg.split(",")
            for a in tools:
                if a not in ALL_TOOLS:
                    print(a + " is not a supported tool.")
                    sys.exit(1)
                if a in C_TOOLS: c_tool = True
                if a in P_TOOLS: p_tool = True

        elif opt == CLASSPATH_ARG:
            aux_classpath_from_file_path = arg
        elif opt == PACKAGE_ARG:
            package = arg

    # check if all the parameters are provided
    if len(args) != 1:
        print("Incorrect arguments.\nFor help read README file or run the script with -h option")
        sys.exit(1)
    project_path = args[0]
    if package is None and p_tool:
        print("\nThere was no -p argument.\nFor help read README file or run the script with -h option")
        sys.exit(1)
    if aux_classpath_from_file_path is None and c_tool:
        print("\nThere was no -c argument.\nFor help read README file or run the script with -h option")
        sys.exit(1)

    # edit project_path, if the path is only a single Java file, go to single_java_file function
    if directory:
        if not project_path.endswith("/"):
            project_path += "/"
        project_path_appsrc = project_path + "app/src/"
        new_package: str = ""
        if package.find("*"):
            new_package = new_package[0:new_package.__len__()-1]
        project_path_package = project_path_appsrc + "main/java/ " + new_package.replace(".", "/")
    else:
        if not project_path.endswith(".java"):
            print("Incorrect arguments.\nArgument for analysing can only be java file or a root directory" +
                  " of Android Studio project")
            sys.exit(1)
        single_java_file(aux_classpath_from_file_path, c_tool, tools, project_path, scores)
        return

    # run selected tools
    for t in tools:
        if t in (SPOTBUGS_4_0_0_BETA4, SPOTBUGS_4_0_0_BETA3, SPOTBUGS_4_0_0_BETA2, SPOTBUGS_4_0_0_BETA1,
                 SPOTBUGS_3_1_12, SPOTBUGS_3_1_0_RC7, SPOTBUGS):
            if t == SPOTBUGS:
                t = SPOTBUGS_4_0_0_BETA4

            sourcepath = "-sourcepath " + project_path_appsrc + "main/java/"
            sourcepath += " -home ./tools/SpotBugs/"

            f1: TextIO = open("./reports/" + t, "w+")

            run = "bash ./tools/SpotBugs/" + t.replace("_", "-") + "/bin/spotbugs -textui -onlyAnalyze " + \
                  package + " -workHard -longBugCodes " + sourcepath + " -output " + get_report_path(t) + \
                  " -auxclasspathFromFile " + aux_classpath_from_file_path + " " + project_path

            process = subprocess.Popen(run, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            process.wait()
            f1.close()

            scores[t] = calculate_score_spotbugs(get_report_path(t))

        elif t == PMD:
            f2: TextIO = open(PMD_REPORT_PATH, "w+")
            file = open(aux_classpath_from_file_path, "r")
            classpaths: List[str] = file.read().split("\n")
            classpaths_modified: str = ""

            for s in classpaths:
                if s:
                    classpaths_modified += s + " "
            classpaths_modified = classpaths_modified.strip().replace(" ", ",")

            run = "bash ./tools/PMD/pmd-bin-6.20.0/bin/run.sh pmd -d " + project_path_appsrc + " -f text -auxclasspath "\
                  + classpaths_modified + " -R ./xmls/rulesets.xml > " + PMD_REPORT_PATH

            process = subprocess.Popen(run, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            process.wait()
            f2.close()

            scores[t] = calculate_score_pmd(get_report_path(t))

        elif t == CPD:
            f3: TextIO = open(CPD_REPORT_PATH, "w+")

            run = "bash ./tools/PMD/pmd-bin-6.20.0/bin/run.sh cpd --minimum-tokens 100 --files " + project_path_appsrc\
                  + " > " + CPD_REPORT_PATH
            process = subprocess.Popen(run, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            process.wait()
            f3.close()

        elif t == GRAUDIT:
            f4: TextIO = open(GRAUDIT_REPORT_PATH, "w+")

            run = "bash ./tools/graudit/graudit -B -z -d android " + project_path_appsrc + " > " + GRAUDIT_REPORT_PATH
            process = subprocess.Popen(run, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            process.wait()
            f4.close()

            scores[t] = calculate_score_graudit(get_report_path(t))

        elif t == CHECKSTYLE:
            f5: TextIO = open(CHECKSTYLE_REPORT_PATH, "w+")

            pattern = "*.java"
            stop: bool = False
            for dirname, subdirList, fileList in os.walk(project_path):
                for file in fnmatch.filter(fileList, pattern):
                    run = "java -jar ./tools/Checkstyle/checkstyle-8.27-all.jar -c ./xmls/checkstyle.xml " + \
                          os.path.join(project_path_package, file) + " >> " + CHECKSTYLE_REPORT_PATH
                    process = subprocess.Popen(run, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    process.wait()
                    stop = True
                    break
                if stop: break
            f5.close()

            scores[t] = calculate_score_checkstyle(get_report_path(t))

    for i in scores:
        print(i, scores[i])
    # generate html report
    generate_html(tools, scores)

    return


def single_java_file(aux_classpath_from_file_path: str, c_tool: bool, tools: Set[str], project_path: str, scores: dict):
    """
    Function for running tools if target is a single Java file.
    """
    if aux_classpath_from_file_path is None and c_tool:
        print("\nThere was no -c argument.\nFor help read README file or run the script with -h option")
        sys.exit(1)

    for t in tools:
        if t in (SPOTBUGS_4_0_0_BETA4, SPOTBUGS_4_0_0_BETA3, SPOTBUGS_4_0_0_BETA2, SPOTBUGS_4_0_0_BETA1,
                 SPOTBUGS_3_1_12, SPOTBUGS_3_1_0_RC7, SPOTBUGS):
            if t == SPOTBUGS:
                t = SPOTBUGS_4_0_0_BETA4

            f1: TextIO = open("./reports/" + t, "w+")

            run = "bash ./tools/SpotBugs/spotbugs-4.0.0-beta4/bin/spotbugs -textui -home ./tools/SpotBugs/ " +\
                  "-workHard -longBugCodes -output " + get_report_path(t) + " -auxclasspathFromFile " +\
                  aux_classpath_from_file_path + " " + project_path

            process = subprocess.Popen(run, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            process.wait()
            f1.close()

            calculate_score_spotbugs(get_report_path(t))

        elif t == PMD:
            f2: TextIO = open(PMD_REPORT_PATH, "w+")
            file = open(aux_classpath_from_file_path, "r")
            classpaths: List[str] = file.read().split("\n")
            classpaths_modified: str = ""

            for s in classpaths:
                if s:
                    classpaths_modified += s + " "
            classpaths_modified = classpaths_modified.strip().replace(" ", ",")

            run = "bash ./tools/PMD/pmd-bin-6.20.0/bin/run.sh pmd -d " + project_path + " -f text -auxclasspath " + \
                  classpaths_modified + " -R ./xmls/rulesets.xml > " + PMD_REPORT_PATH

            process = subprocess.Popen(run, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            process.wait()
            f2.close()

            calculate_score_pmd(get_report_path(t))

        elif t == CPD:
            f3: TextIO = open(CPD_REPORT_PATH, "w+")

            run = "bash ./tools/PMD/pmd-bin-6.20.0/bin/run.sh cpd --minimum-tokens 100 --files " + project_path + \
                  " > " + CPD_REPORT_PATH
            process = subprocess.Popen(run, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            process.wait()
            f3.close()

        elif t == GRAUDIT:
            f4: TextIO = open(GRAUDIT_REPORT_PATH, "w+")

            run = "bash ./tools/graudit/graudit -B -z -d android " + project_path + " > " + GRAUDIT_REPORT_PATH
            process = subprocess.Popen(run, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            process.wait()
            f4.close()

            calculate_score_graudit(get_report_path(t))

        elif t == CHECKSTYLE:
            f5: TextIO = open(CHECKSTYLE_REPORT_PATH, "w+")

            run = "java -jar ./tools/Checkstyle/checkstyle-8.27-all.jar -c ./xmls/checkstyle.xml " + \
                  project_path + " >> " + CHECKSTYLE_REPORT_PATH
            process = subprocess.Popen(run, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            process.wait()
            f5.close()

            calculate_score_checkstyle(get_report_path(t))

        # generate html report
        generate_html(tools, scores)

    return


def generate_html(tools: Set[str], scores: dict):
    """
    Generates html report
    """
    with open("report.html", "w+") as f:
        f.write("<!DOCTYPE html>\n<html lang=\"hr\">\n")
        head = HeadBlock()
        f.write(str(head))
        f.write("\n<body>\n")
        body = generate_body(tools, scores)
        f.write(body)
        f.write("\n</body>\n")
        f.write("\n</html>\n")


def generate_body(tools: Set[str], scores: dict) -> str:
    """
    Generates html body for our report
    :param scores: dictionary, stores scores of all used tools
    :param tools: all the tools selected by user
    :return: string representation of html body
    """
    body: str = ""

    body += "\n<meta charset=\"utf-8\">"

    list_element = htmlgen.OrderedList()
    for t in tools:
        list_element.create_item(htmlgen.Link("#" + t, t))
    list_element.create_item(htmlgen.Link("#table", "table"))
    body += str(list_element)

    for i in range(0, 3):
        body += "\n<br>"

    text: str = ""
    for t in tools:
        for i in range(0, 2):
            body += "\n<br>"
        body += "\n<h3 id=\"" + t + "\" style=\"background-color:powderblue;color:red\">" + t + "</h3>\n"

        with open(get_report_path(t), "r") as file:
            file_text = file.read().replace("\n", "<br>")
            text = file_text + "\n"
        body += text

    for i in range(0, 6):
        body += "\n<br>"
    body += "\n<h3 id=\"table\">table</h3>\n"

    # add table of rankings
    table = htmlgen.Table()
    head = table.create_simple_header_row("TOOL", "SCORE")
    for key in scores:
        row = table.create_row()
        cell1 = row.create_cell(str(key))
        cell2 = row.create_cell(str(scores[key]))
    with open("table_formatting", "r") as css_formatting:
        body += "<style>\n" + css_formatting.read() + "</style>\n"

    body += str(table)

    return body


def get_report_path(t: str) -> str:
    """
    Returns the path of report of tool t. Uses utils constants.
    :param t: tool whose report path is returned
    :return: path of tool report
    """
    if t == SPOTBUGS: return SPOTBUGS_4_0_0_BETA4_REPORT_PATH
    if t == SPOTBUGS_4_0_0_BETA4: return SPOTBUGS_4_0_0_BETA4_REPORT_PATH
    if t == SPOTBUGS_4_0_0_BETA3: return SPOTBUGS_4_0_0_BETA3_REPORT_PATH
    if t == SPOTBUGS_4_0_0_BETA2: return SPOTBUGS_4_0_0_BETA2_REPORT_PATH
    if t == SPOTBUGS_4_0_0_BETA1: return SPOTBUGS_4_0_0_BETA1_REPORT_PATH
    if t == CHECKSTYLE: return CHECKSTYLE_REPORT_PATH
    if t == GRAUDIT: return GRAUDIT_REPORT_PATH
    if t == CPD: return CPD_REPORT_PATH
    if t == PMD: return PMD_REPORT_PATH


class HeadBlock(htmlgen.Head):
    """
    Class for making html head
    """
    def __init__(self):
        super(HeadBlock, self).__init__()

    def generate_children(self):
        yield "Static source code analysis report"


def calculate_score_spotbugs(file: str) -> int:
    """
    Calculates the score for spotbugs tool.
    Spotbugs tool finds security issues, data leaks, resource cleanup problems etc. That's why it gets +10 points for
    every found problem. The tool often reports problems in R.java file. Lines containing problems in that file will
    be ignored in this score calculation.

    :param file: report file generated by spotbugs
    :return: the int score
    """
    if not os.path.isfile(file):
        raise OSError()

    score: int = 0
    with open(file, "r") as f:
        lines = f.readlines()
        for line in lines:
            if "R.java" in line:
                continue
            score += 10

    return score


def calculate_score_checkstyle(file: str) -> int:
    """
    Calculates the score for checkstyle tool.
    Since it's a style checker rather than security analyser tool, it will get +1 for every found error. Errors which
    report following malpractices are ignored because of large number of false positives:
    - lines that are longer than 80 characters
    - operator wraps
    - parameters that should be final
    - classes look like designed for extension

    Reporting of those code style errors is due to sun's xml file which was used while running the checkstyle tool.
    sun_checks.xml defines good coding practices and is often used with checkstyle.
    see:
        https://github.com/checkstyle/checkstyle/blob/master/src/main/resources/sun_checks.xml)

    :param file: report file generated by checkstyle
    :return: the int score
    """
    if not os.path.isfile(file):
        raise OSError()

    score: int = 0
    with open(file, "r") as f:
        lines = f.readlines()
        for line in lines:
            if "Line is longer than 80 characters" in line or "should be final. [FinalParameters]" in line \
                    or "should be on a new line. [OperatorWrap]" in line \
                    or "looks like designed for extension (can be subclassed)" in line:
                continue
            score += 1

    return score


def calculate_score_graudit(file: str) -> int:
    """
    Calculates the score for graudit tool.
    Unlike other tools, graudit doesn't explain which issue is found and just shows the context around the issue. This
    results in a lengthy report, but also much more difficult bug fix process, and thus it gets deducted points. All the
    lines which are context, and not actual mistakes, are ignored, and the amount of points is calculated by
    the algorithm:
        the number of separators found + 1 (separator is "####...", the number of separators equals the number of
        issues found, but the first issue doesn't start with separator and the last issue doesn't end with separator),
        divided by 2 and rounded to the nearest whole number

    :param file: report file generated by graudit
    :return: the int score
    """
    if not os.path.isfile(file):
        raise OSError()

    score: int = 1
    with open(file, "r") as f:
        lines = f.readlines()
        for line in lines:
            if "#############" in line:
                score += 1

    return int(round(score/2, 0))


def calculate_score_pmd(file: str) -> int:
    """
    Calculates the score for PMD tool.
    It will get +1 for every found error. Found errors that will be ignored:
    - local variables that could be declared final
    - parameters not assigned which could be declared final
    - potential violation of Law of Demeter

    :param file: report file generated by PMD
    :return: the int score
    """
    if not os.path.isfile(file):
        raise OSError()

    score: int = 0
    with open(file, "r") as f:
        lines = f.readlines()
        for line in lines:
            if "Potential violation of Law of Demeter" in line or "could be declared final" in line:
                continue
            score += 1

    return score


if __name__ == '__main__':
    main(sys.argv[1:])