# import all library needed for this class
import json

from openrefine_client_master.google.refine import refine
from itertools import groupby
import StringIO
from subprocess import call
import subprocess
import uuid
import base64
import os
import time
#from graphviz import Digraph

class OR2YW:
    def __init__(self, server_host="localhost", server_port="3333", doc_root="/"):
        """
        Init function for this class, put any initialization attributes that you need here

        """
        self.server_host = server_host
        self.server_port = server_port
        self.doc_root = doc_root

    def get_projects(self):
        """
        return the list of projects (project_id,name) and or some rows sample for all projects in the server
        :return:
        >>> OR2YW().get_projects() # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
        {...}
        """
        return refine.Refine(
            refine.RefineServer(refine_port=self.server_port, refine_host=self.server_host)).list_projects()

    def get_json(self, id):
        """
        id: project id which we want to create workflow with
        return the list of operations (json/dictionary) gathered using ORClientAPI
        :return:
        >>> sample_id = "2438670021504"
        >>> OR2YW().get_json(sample_id) # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
        {...}
        """
        outputs = refine.RefineProject(refine.RefineServer(refine_port=self.server_port, refine_host=self.server_host),
                                       refine_port=self.server_port, refine_host=self.server_host,
                                       project_id=id).get_operations()
        return json.loads(outputs.read())

    @staticmethod
    def generate_yw_script(operations):
        """
        given a list of operations in dictionary format, return yes workflow script in text
        id: list of operations dictionary / json format
        return yw_script (text / string)
        :return:
        """
        temp_data = [x["operation"] for x in operations]
        data = []
        for tdata in temp_data:
            if "columnName" in tdata.keys():
                data.append(tdata)

        print(json.dumps(data))
        # first part rename and output dtable
        rename_c = 0



        for dicts in data:
            if dicts['op'] == 'core/column-rename':
                rename_c += 1
        # sort the left to parallel the operations
        data[rename_c:] = sorted(data[rename_c:], key=lambda k: k['columnName'])

        # groupby the columnName
        list_of_lists = []
        newdata = data[rename_c:]
        for key, group in groupby(newdata, lambda x: x['columnName'].split()[0]):
            list_of_lists.append(list(group))
        # pprint(list_of_lists)

        splitlists = []
        # separate Split schema operation
        for innerlists in list_of_lists:
            for innerdicts in innerlists:
                if innerdicts['op'] == 'core/column-split':
                    splitlists.append(innerlists)

        # substraction of the list of lists of dicts
        newlist_of_lists = [item for item in list_of_lists if item not in splitlists]

        # print all of the #@in
        inputdatalist = []
        for dicts in data:
            # print('#@begin '+dicts['op']+'#@desc '+dicts['description']+'\n')
            if dicts['op'] == 'core/column-rename':
                # print('#@in '+dicts['oldColumnName']+'\n')
                # print('#@in '+dicts['newColumnName']+'\n')
                oldColumnName = 'oldColumnName:' + dicts['oldColumnName']
                newColumnName = 'newColumnName:' + dicts['newColumnName']
                inputdatalist.append(oldColumnName)
                inputdatalist.append(newColumnName)

            elif dicts['op'] == 'core/mass-edit':
                colname = 'col-name:' + dicts['columnName']
                inputdatalist.append(colname)
            elif dicts['op'] == 'core/text-transform':
                colname = 'col-name:' + dicts['columnName']
                expression = 'expression:' + dicts['expression']
                inputdatalist.append(colname)
                inputdatalist.append(expression)
            elif dicts['op'] == 'core/column-split':
                colname = 'col-name:' + dicts['columnName']
                separator = 'separator:' + '"%s"' % (dicts['separator'])
                remove = 'removeOriginalColumn:%s' % dicts['removeOriginalColumn']
                inputdatalist.append(colname)
                inputdatalist.append(separator)
                inputdatalist.append(remove)
        deinputdatalist = set(inputdatalist)

        # count how many steps for schema level
        table_counter = 0
        # rename operations and split operations
        for dicts in data:
            if dicts['op'] == 'core/column-rename' or dicts['op'] == 'core/column-split':
                table_counter += 1

        outtable = table_counter + 1

        # parse into YW model
        # create a string buffer instead
        # f = open('../yw/2Original_SPParseYW.txt', 'w')
        f = StringIO.StringIO()
        f.write('#@begin SPOriginalOR2#@desc Workflow of Linear original openrefine history\n')
        for sublist in list(deinputdatalist):
            f.write('#@param ' + sublist + '\n')
        f.write('#@in table0\n')
        f.write('#@out table%d\n' % outtable)
        table_c = 0
        i = 0
        # rename operations
        for dicts in data[:rename_c]:
            if dicts['op'] == 'core/column-rename':
                f.write('#@begin core/column-rename%d' % i + '#@desc ' + dicts['description'] + '\n')
                f.write('#@param oldColumnName:' + dicts['oldColumnName'] + '\n')
                f.write('#@param newColumnName:' + dicts['newColumnName'] + '\n')
                f.write('#@in table%d\n' % table_c)
                table_c += 1
                f.write('#@out table%d\n' % table_c)
                f.write('#@end core/column-rename%d\n' % i)
                i += 1

        # operations on column (column level)
        # schema level
        def ruleforreturn(ind, tc, colname, table_counter):

            # [{'columnName':Sponsor, 'function':value.toNumber()},{....}]
            # [{'columnName':event, 'function':value.toDate()},{.....}]
            if ind == 0:
                f.write('#@in table%d\n' % table_counter)
                f.write('#@out %s%d\n' % (colname, tc))
            else:
                f.write('#@in %s%d\n' % (colname, tc - 1))
                f.write('#@out %s%d\n' % (colname, tc))

        # Schema level (Rename, Split)

        massedit_c = 0
        texttrans_c = 0

        for lists in newlist_of_lists:
            count = 0
            tc = 1
            for dicts in lists:
                col_name = 'col:%s' % dicts['columnName']
                if dicts['op'] == 'core/mass-edit':
                    f.write('#@begin core/mass-edit%d' % massedit_c + '#@desc ' + dicts['description'] + '\n')
                    f.write('#@param col-name:' + dicts['columnName'] + '\n')
                    ruleforreturn(count, tc, col_name, table_c)
                    tc += 1
                    count += 1
                    f.write('#@end core/mass-edit%d\n' % massedit_c)
                    massedit_c += 1
                elif dicts['op'] == 'core/text-transform':
                    f.write('#@begin core/text-transform%d' % texttrans_c + '#@desc ' + dicts['description'] + '\n')
                    f.write('#@param col-name:' + dicts['columnName'] + '\n')
                    f.write('#@param expression:' + dicts['expression'] + '\n')
                    ruleforreturn(count, tc, col_name, table_c)
                    tc += 1
                    count += 1
                    f.write('#@end core/text-transform%d\n' % texttrans_c)
                    texttrans_c += 1

            # f.write('#@end OperationsOn%s\n'%list_of_sublists[a][0])
        colsplit_c = 0
        dtable_c = table_c

        def ruleforsplitreturn(index, tc, columnName, column_counter):
            if index == 0:
                f.write('#@in table%d\n' % tc)
                column_counter += 1
                f.write('#@out col:%s%d\n' % (columnName, column_counter))
            else:
                f.write('#@in col:%s%d\n' % (columnName, column_counter))
                column_counter += 1
                f.write('#@out col:%s%d\n' % (columnName, column_counter))

        outerlenth = len(splitlists)

        for a in range(outerlenth):
            innerlenth = len(splitlists[a])
            if splitlists[a][0]['op'] == 'core/column-split':
                f.write('#@begin core/column-split%d' % colsplit_c + '#@desc %s\n' % (
                    splitlists[a][0]['description']) + '\n')
                f.write('#@param separator:"%s"\n' % (splitlists[a][0]['separator']))
                f.write('#@param removeOriginalColumn:%s\n' % splitlists[a][0]['removeOriginalColumn'])
                f.write('#@param col-name:%s\n' % splitlists[a][0]['columnName'])
                f.write('#@in table%d\n' % dtable_c)
                dtable_c += 1
                f.write('#@out table%d\n' % dtable_c)
                f.write('#@end core/column-split%d\n' % colsplit_c)
                colsplit_c += 1
                ind = 0
                col_counter = 0
                columnName = splitlists[a][0]['columnName']
                for b in range(1, innerlenth):
                    opname = splitlists[a][b]['op']
                    if opname == 'core/mass-edit':
                        f.write('#@begin core/mass-edit%d' % massedit_c + '#@desc ' + splitlists[a][b][
                            'description'] + '\n')
                        f.write('#@param col-name:"%s"\n' % splitlists[a][b]['columnName'])
                        ruleforsplitreturn(ind, dtable_c, columnName, col_counter)
                        col_counter += 1
                        ind += 1
                        f.write('#@end core/mass-edit%d\n' % massedit_c)
                        massedit_c += 1
                    elif opname == 'core/text-transform':
                        f.write('#@begin core/text-transform%d' % texttrans_c + '#@desc ' + splitlists[a][b][
                            'description'] + '\n')
                        f.write('#@param col-name:' + splitlists[a][b]['columnName'] + '\n')
                        f.write('#@param expression:' + splitlists[a][b]['expression'] + '\n')
                        ruleforsplitreturn(ind, dtable_c, columnName, col_counter)
                        col_counter += 1
                        ind += 1
                        f.write('#@end core/text-transform%d\n' % texttrans_c)
                        texttrans_c += 1
            elif splitlists[a][0]['op'] == 'core/mass-edit':
                columnName = splitlists[a][0]['columnName']
                col_counter = 1
                f.write('#@begin core/mass-edit%d' % massedit_c + '#@desc ' + splitlists[a][0]['description'] + '\n')
                f.write('#@param col-name:"%s"\n' % splitlists[a][0]['columnName'])
                f.write('#@in table%d\n' % dtable_c)
                f.write('#@out col:%s%d\n' % (columnName, col_counter))
                massedit_c += 1
                f.write('#@end core/mass-edit%d\n' % massedit_c)
                for b in range(1, innerlenth):
                    if splitlists[a][b]['op'] == 'core/column-split':
                        innerindex = 0
                        for j in range(1, b):
                            if splitlists[a][j]['op'] == 'core/mass-edit':
                                f.write('#@begin core/mass-edit%d' % massedit_c + '#@desc ' + splitlists[a][j][
                                    'description'] + '\n')
                                f.write('#@param col-name:"%s"\n' % splitlists[a][j]['columnName'])
                                f.write('#@in col:%s%d\n' % (columnName, col_counter))
                                col_counter += 1
                                f.write('#@out col:%s%d\n' % (columnName, col_counter))
                                f.write('#@end core/mass-edit%d\n' % massedit_c)
                                massedit_c += 1
                            elif splitlists[a][j]['op'] == 'core/text-transform':
                                f.write('#@begin core/text-transform%d' % texttrans_c + '#@desc ' + splitlists[a][j][
                                    'description'] + '\n')
                                f.write('#@param col-name:' + splitlists[a][j]['columnName'] + '\n')
                                f.write('#@param expression:' + splitlists[a][j]['expression'] + '\n')
                                f.write('#@in col:%s%d\n' % (columnName, col_counter))
                                col_counter += 1
                                f.write('#@out col:%s%d\n' % (columnName, col_counter))
                                f.write('#@end core/text-transform%d\n' % texttrans_c)
                                texttrans_c += 1
                        f.write('#@begin core/column-split%d' % colsplit_c + '#@desc %s\n' % (
                            splitlists[a][b]['description']) + '\n')
                        f.write('#@param separator:"%s"\n' % (splitlists[a][b]['separator']))
                        f.write('#@param removeOriginalColumn:%s\n' % splitlists[a][b]['removeOriginalColumn'])
                        f.write('#@param col-name:%s\n' % splitlists[a][b]['columnName'])
                        f.write('#@in col:%s%d\n' % (columnName, b))
                        dtable_c += 1
                        f.write('#@out table%d\n' % dtable_c)
                        f.write('#@end core/column-split%d\n' % colsplit_c)
                        colsplit_c += 1
                        for k in range(b + 1, innerlenth):
                            if splitlists[a][k]['op'] == 'core/mass-edit':
                                f.write('#@begin core/mass-edit%d' % massedit_c + '#@desc ' + splitlists[a][k][
                                    'description'] + '\n')
                                f.write('#@param col-name:"%s"\n' % splitlists[a][k]['columnName'])
                                ruleforsplitreturn(innerindex, dtable_c, columnName, col_counter)
                                innerindex += 1
                                col_counter += 1
                                f.write('#@end core/mass-edit%d\n' % massedit_c)
                                massedit_c += 1
                            elif splitlists[a][k]['op'] == 'core/text-transform':
                                f.write('#@begin core/text-transform%d' % texttrans_c + '#@desc ' + splitlists[a][k][
                                    'description'] + '\n')
                                f.write('#@param col-name:' + splitlists[a][k]['columnName'] + '\n')
                                f.write('#@param expression:' + splitlists[a][k]['expression'] + '\n')
                                ruleforsplitreturn(innerindex, dtable_c, columnName, col_counter)
                                innerindex += 1
                                col_counter += 1
                                f.write('#@end core/text-transform%d\n' % texttrans_c)
                                texttrans_c += 1
            elif splitlists[a][0]['op'] == 'core/text-transform':
                columnName = splitlists[a][0]['columnName']
                col_counter = 1
                f.write(
                    '#@begin core/text-transform%d' % texttrans_c + '#@desc ' + splitlists[a][0]['description'] + '\n')
                f.write('#@param col-name:' + splitlists[a][0]['columnName'] + '\n')
                f.write('#@param expression:' + splitlists[a][0]['expression'] + '\n')
                f.write('#@in table%d\n' % dtable_c)
                f.write('#@out col:%s%d\n' % (columnName, col_counter))
                texttrans_c += 1
                f.write('#@end core/text-transform%d\n' % texttrans_c)
                for b in range(1, innerlenth):
                    if splitlists[a][b]['op'] == 'core/column-split':
                        innerindex = 0
                        for j in range(1, b):
                            if splitlists[a][j]['op'] == 'core/mass-edit':
                                f.write('#@begin core/mass-edit%d' % massedit_c + '#@desc ' + splitlists[a][j][
                                    'description'] + '\n')
                                f.write('#@param col-name:"%s"\n' % splitlists[a][j]['columnName'])
                                f.write('#@in col:%s%d\n' % (columnName, col_counter))
                                col_counter += 1
                                f.write('#@out col:%s%d\n' % (columnName, col_counter))
                                f.write('#@end core/mass-edit%d\n' % massedit_c)
                                massedit_c += 1
                            elif splitlists[a][j]['op'] == 'core/text-transform':
                                f.write('#@begin core/text-transform%d' % texttrans_c + '#@desc ' + splitlists[a][j][
                                    'description'] + '\n')
                                f.write('#@param col-name:' + splitlists[a][j]['columnName'] + '\n')
                                f.write('#@param expression:' + splitlists[a][j]['expression'] + '\n')
                                f.write('#@in col:%s%d\n' % (columnName, col_counter))
                                col_counter += 1
                                f.write('#@out col:%s%d\n' % (columnName, col_counter))
                                f.write('#@end core/text-transform%d\n' % texttrans_c)
                                texttrans_c += 1
                        f.write('#@begin core/column-split%d' % colsplit_c + '#@desc %s\n' % (
                            splitlists[a][b]['description']) + '\n')
                        f.write('#@param separator:"%s"\n' % (splitlists[a][b]['separator']))
                        f.write('#@param removeOriginalColumn:%s\n' % splitlists[a][b]['removeOriginalColumn'])
                        f.write('#@param col-name:%s\n' % splitlists[a][b]['columnName'])
                        f.write('#@in col:%s%d\n' % (columnName, b))
                        dtable_c += 1
                        f.write('#@out table%d\n' % dtable_c)
                        f.write('#@end core/column-split%d\n' % colsplit_c)
                        colsplit_c += 1
                        for k in range(b + 1, innerlenth):
                            if splitlists[a][k]['op'] == 'core/mass-edit':
                                f.write('#@begin core/mass-edit%d' % massedit_c + '#@desc ' + splitlists[a][k][
                                    'description'] + '\n')
                                f.write('#@param col-name:"%s"\n' % splitlists[a][k]['columnName'])
                                ruleforsplitreturn(innerindex, dtable_c, columnName, col_counter)
                                innerindex += 1
                                col_counter += 1
                                f.write('#@end core/mass-edit%d\n' % massedit_c)
                                massedit_c += 1
                            elif splitlists[a][k]['op'] == 'core/text-transform':
                                f.write('#@begin core/text-transform%d' % texttrans_c + '#@desc ' + splitlists[a][k][
                                    'description'] + '\n')
                                f.write('#@param col-name:' + splitlists[a][k]['columnName'] + '\n')
                                f.write('#@param expression:' + splitlists[a][k]['expression'] + '\n')
                                ruleforsplitreturn(innerindex, dtable_c, columnName, col_counter)
                                innerindex += 1
                                col_counter += 1
                                f.write('#@end core/text-transform%d\n' % texttrans_c)
                                texttrans_c += 1

        f.write('#@begin MergeOperationsColumns #@desc Merge the Parallel Column operations\n')
        for m in range(len(newlist_of_lists)):
            newcol_name = 'col:%s' % (newlist_of_lists[m][0]['columnName'])
            colcounter = len(newlist_of_lists[m])
            f.write('#@in %s%d\n' % (newcol_name, colcounter))

        for n in range(len(splitlists)):
            lenthdicts = len(splitlists[n])
            if splitlists[n][lenthdicts - 1]['op'] == 'core/column-split':
                f.write('#@in table%d\n' % dtable_c)
            else:
                col_c = lenthdicts - 1
                f.write('#@in col:%s%d\n' % (splitlists[n][0]['columnName'], col_c))

        outtable = dtable_c + 1
        f.write('#@out table%d\n' % outtable)
        f.write('#@end MergeOperationsColumns\n')

        f.write('#@end SPOriginalOR2\n')
        output_string = f.getvalue()
        f.close()

        return output_string


    @staticmethod
    def generate_yw_image(yw_script, java_file=None,dot_file=None , image_type=None):
        """
        given a yw_script return the image based on choice
        id: yw_script string
        return binary image
        :return:
        """
        #import subprocess
        # create temporary file

        # generate unique id for image creation
        try:
            temp_folder = ""
            tempid = str(uuid.uuid4())
            text_name = "tmp-"+tempid+".txt"
            gv_name = "tmp-"+tempid+".gv"
            png_name = "tmp-"+tempid+".png"
            with open(temp_folder+text_name, "w") as f:
                f.write(yw_script)

            cmd = "cat {} | {} -jar yesworkflow-0.2.2.0-SNAPSHOT-jar-with-dependencies.jar graph -c extract.comment='#' > {}".format(temp_folder+text_name,java_file,temp_folder+gv_name)
            ps = subprocess.Popen(cmd, shell=True)
            # ps = subprocess.Popen(["cat","tmp.txt"])
            ps.wait()
            #time.sleep(5)

            # call(cmd)
            cmd = "{} -Tpng {} -o {}".format(dot_file,temp_folder+gv_name,temp_folder+png_name)
            # dot -Tpng gv/Linear.gv -o png/Linear.png
            print(cmd)
            ps = subprocess.Popen(cmd, shell=True)
            #ps = subprocess.Popen(["/opt/local/bin/dot","-Tpng",temp_folder+gv_name,"-o",temp_folder+png_name])
            ps.wait()

            #dot = Digraph(comment="workflow")
            #dot.render(temp_folder+gv_name,view=True)

            encoded = base64.b64encode(open(temp_folder+png_name, "rb").read())
            return (encoded, temp_folder+png_name)
        finally:
            # delete the temporary files
            #os.remove(temp_folder+text_name)
            #os.remove(temp_folder+gv_name)
            #os.remove(temp_folder+png_name)
            pass

class OR2YWGenerator:
    @staticmethod
    def generate_yw_image(yw_script, image_type=None):
        """
        given a yw_script return the image based on choice
        id: yw_script string
        return binary image
        :return:
        """
        #import subprocess
        # create temporary file

        # generate unique id for image creation
        temp_folder = "/tmp/"
        tempid = str(uuid.uuid4())
        text_name = "tmp-"+tempid+".txt"
        gv_name = "tmp-"+tempid+".gv"
        png_name = "tmp-"+tempid+".png"
        with open(temp_folder+text_name, "w") as f:
            f.write(yw_script)

        cmd = "cat {} | java -jar yesworkflow-0.2.2.0-SNAPSHOT-jar-with-dependencies.jar graph -c extract.comment='#' > {}".format(temp_folder+text_name,temp_folder+gv_name)
        ps = subprocess.Popen(cmd, shell=True)
        # ps = subprocess.Popen(["cat","tmp.txt"])
        ps.wait()
        # call(cmd)
        cmd = "dot -Tpng {} -o {}".format(temp_folder+gv_name,temp_folder+png_name)
        # dot -Tpng gv/Linear.gv -o png/Linear.png
        ps = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        ps.wait()
        encoded = base64.b64encode(open(temp_folder+png_name, "rb").read())


        # delete the temporary files
        os.remove(temp_folder+text_name)
        os.remove(temp_folder+gv_name)
        os.remove(temp_folder+png_name)
        return encoded


    @staticmethod
    def generate_yw_script(operations):
        """
        given a list of operations in dictionary format, return yes workflow script in text
        id: list of operations dictionary / json format
        return yw_script (text / string)
        :return:
        """
        data = [x["operation"] for x in operations]
        # first part rename and output dtable
        rename_c = 0
        for dicts in data:
            if dicts['op'] == 'core/column-rename':
                rename_c += 1
        # sort the left to parallel the operations
        data[rename_c:] = sorted(data[rename_c:], key=lambda k: k['columnName'])

        # groupby the columnName
        list_of_lists = []
        newdata = data[rename_c:]
        for key, group in groupby(newdata, lambda x: x['columnName'].split()[0]):
            list_of_lists.append(list(group))
        # pprint(list_of_lists)

        splitlists = []
        # separate Split schema operation
        for innerlists in list_of_lists:
            for innerdicts in innerlists:
                if innerdicts['op'] == 'core/column-split':
                    splitlists.append(innerlists)

        # substraction of the list of lists of dicts
        newlist_of_lists = [item for item in list_of_lists if item not in splitlists]

        # print all of the #@in
        inputdatalist = []
        for dicts in data:
            # print('#@begin '+dicts['op']+'#@desc '+dicts['description']+'\n')
            if dicts['op'] == 'core/column-rename':
                # print('#@in '+dicts['oldColumnName']+'\n')
                # print('#@in '+dicts['newColumnName']+'\n')
                oldColumnName = 'oldColumnName:' + dicts['oldColumnName']
                newColumnName = 'newColumnName:' + dicts['newColumnName']
                inputdatalist.append(oldColumnName)
                inputdatalist.append(newColumnName)

            elif dicts['op'] == 'core/mass-edit':
                colname = 'col-name:' + dicts['columnName']
                inputdatalist.append(colname)
            elif dicts['op'] == 'core/text-transform':
                colname = 'col-name:' + dicts['columnName']
                expression = 'expression:' + dicts['expression']
                inputdatalist.append(colname)
                inputdatalist.append(expression)
            elif dicts['op'] == 'core/column-split':
                colname = 'col-name:' + dicts['columnName']
                separator = 'separator:' + '"%s"' % (dicts['separator'])
                remove = 'removeOriginalColumn:%s' % dicts['removeOriginalColumn']
                inputdatalist.append(colname)
                inputdatalist.append(separator)
                inputdatalist.append(remove)
        deinputdatalist = set(inputdatalist)

        # count how many steps for schema level
        table_counter = 0
        # rename operations and split operations
        for dicts in data:
            if dicts['op'] == 'core/column-rename' or dicts['op'] == 'core/column-split':
                table_counter += 1

        outtable = table_counter + 1

        # parse into YW model
        # create a string buffer instead
        # f = open('../yw/2Original_SPParseYW.txt', 'w')
        f = StringIO.StringIO()
        f.write('#@begin SPOriginalOR2#@desc Workflow of Linear original openrefine history\n')
        for sublist in list(deinputdatalist):
            f.write('#@param ' + sublist + '\n')
        f.write('#@in table0\n')
        f.write('#@out table%d\n' % outtable)
        table_c = 0
        i = 0
        # rename operations
        for dicts in data[:rename_c]:
            if dicts['op'] == 'core/column-rename':
                f.write('#@begin core/column-rename%d' % i + '#@desc ' + dicts['description'] + '\n')
                f.write('#@param oldColumnName:' + dicts['oldColumnName'] + '\n')
                f.write('#@param newColumnName:' + dicts['newColumnName'] + '\n')
                f.write('#@in table%d\n' % table_c)
                table_c += 1
                f.write('#@out table%d\n' % table_c)
                f.write('#@end core/column-rename%d\n' % i)
                i += 1

        # operations on column (column level)
        # schema level
        def ruleforreturn(ind, tc, colname, table_counter):

            # [{'columnName':Sponsor, 'function':value.toNumber()},{....}]
            # [{'columnName':event, 'function':value.toDate()},{.....}]
            if ind == 0:
                f.write('#@in table%d\n' % table_counter)
                f.write('#@out %s%d\n' % (colname, tc))
            else:
                f.write('#@in %s%d\n' % (colname, tc - 1))
                f.write('#@out %s%d\n' % (colname, tc))

        # Schema level (Rename, Split)

        massedit_c = 0
        texttrans_c = 0

        for lists in newlist_of_lists:
            count = 0
            tc = 1
            for dicts in lists:
                col_name = 'col:%s' % dicts['columnName']
                if dicts['op'] == 'core/mass-edit':
                    f.write('#@begin core/mass-edit%d' % massedit_c + '#@desc ' + dicts['description'] + '\n')
                    f.write('#@param col-name:' + dicts['columnName'] + '\n')
                    ruleforreturn(count, tc, col_name, table_c)
                    tc += 1
                    count += 1
                    f.write('#@end core/mass-edit%d\n' % massedit_c)
                    massedit_c += 1
                elif dicts['op'] == 'core/text-transform':
                    f.write('#@begin core/text-transform%d' % texttrans_c + '#@desc ' + dicts['description'] + '\n')
                    f.write('#@param col-name:' + dicts['columnName'] + '\n')
                    f.write('#@param expression:' + dicts['expression'] + '\n')
                    ruleforreturn(count, tc, col_name, table_c)
                    tc += 1
                    count += 1
                    f.write('#@end core/text-transform%d\n' % texttrans_c)
                    texttrans_c += 1

            # f.write('#@end OperationsOn%s\n'%list_of_sublists[a][0])
        colsplit_c = 0
        dtable_c = table_c

        def ruleforsplitreturn(index, tc, columnName, column_counter):
            if index == 0:
                f.write('#@in table%d\n' % tc)
                column_counter += 1
                f.write('#@out col:%s%d\n' % (columnName, column_counter))
            else:
                f.write('#@in col:%s%d\n' % (columnName, column_counter))
                column_counter += 1
                f.write('#@out col:%s%d\n' % (columnName, column_counter))

        outerlenth = len(splitlists)

        for a in range(outerlenth):
            innerlenth = len(splitlists[a])
            if splitlists[a][0]['op'] == 'core/column-split':
                f.write('#@begin core/column-split%d' % colsplit_c + '#@desc %s\n' % (
                    splitlists[a][0]['description']) + '\n')
                f.write('#@param separator:"%s"\n' % (splitlists[a][0]['separator']))
                f.write('#@param removeOriginalColumn:%s\n' % splitlists[a][0]['removeOriginalColumn'])
                f.write('#@param col-name:%s\n' % splitlists[a][0]['columnName'])
                f.write('#@in table%d\n' % dtable_c)
                dtable_c += 1
                f.write('#@out table%d\n' % dtable_c)
                f.write('#@end core/column-split%d\n' % colsplit_c)
                colsplit_c += 1
                ind = 0
                col_counter = 0
                columnName = splitlists[a][0]['columnName']
                for b in range(1, innerlenth):
                    opname = splitlists[a][b]['op']
                    if opname == 'core/mass-edit':
                        f.write('#@begin core/mass-edit%d' % massedit_c + '#@desc ' + splitlists[a][b][
                            'description'] + '\n')
                        f.write('#@param col-name:"%s"\n' % splitlists[a][b]['columnName'])
                        ruleforsplitreturn(ind, dtable_c, columnName, col_counter)
                        col_counter += 1
                        ind += 1
                        f.write('#@end core/mass-edit%d\n' % massedit_c)
                        massedit_c += 1
                    elif opname == 'core/text-transform':
                        f.write('#@begin core/text-transform%d' % texttrans_c + '#@desc ' + splitlists[a][b][
                            'description'] + '\n')
                        f.write('#@param col-name:' + splitlists[a][b]['columnName'] + '\n')
                        f.write('#@param expression:' + splitlists[a][b]['expression'] + '\n')
                        ruleforsplitreturn(ind, dtable_c, columnName, col_counter)
                        col_counter += 1
                        ind += 1
                        f.write('#@end core/text-transform%d\n' % texttrans_c)
                        texttrans_c += 1
            elif splitlists[a][0]['op'] == 'core/mass-edit':
                columnName = splitlists[a][0]['columnName']
                col_counter = 1
                f.write('#@begin core/mass-edit%d' % massedit_c + '#@desc ' + splitlists[a][0]['description'] + '\n')
                f.write('#@param col-name:"%s"\n' % splitlists[a][0]['columnName'])
                f.write('#@in table%d\n' % dtable_c)
                f.write('#@out col:%s%d\n' % (columnName, col_counter))
                massedit_c += 1
                f.write('#@end core/mass-edit%d\n' % massedit_c)
                for b in range(1, innerlenth):
                    if splitlists[a][b]['op'] == 'core/column-split':
                        innerindex = 0
                        for j in range(1, b):
                            if splitlists[a][j]['op'] == 'core/mass-edit':
                                f.write('#@begin core/mass-edit%d' % massedit_c + '#@desc ' + splitlists[a][j][
                                    'description'] + '\n')
                                f.write('#@param col-name:"%s"\n' % splitlists[a][j]['columnName'])
                                f.write('#@in col:%s%d\n' % (columnName, col_counter))
                                col_counter += 1
                                f.write('#@out col:%s%d\n' % (columnName, col_counter))
                                f.write('#@end core/mass-edit%d\n' % massedit_c)
                                massedit_c += 1
                            elif splitlists[a][j]['op'] == 'core/text-transform':
                                f.write('#@begin core/text-transform%d' % texttrans_c + '#@desc ' + splitlists[a][j][
                                    'description'] + '\n')
                                f.write('#@param col-name:' + splitlists[a][j]['columnName'] + '\n')
                                f.write('#@param expression:' + splitlists[a][j]['expression'] + '\n')
                                f.write('#@in col:%s%d\n' % (columnName, col_counter))
                                col_counter += 1
                                f.write('#@out col:%s%d\n' % (columnName, col_counter))
                                f.write('#@end core/text-transform%d\n' % texttrans_c)
                                texttrans_c += 1
                        f.write('#@begin core/column-split%d' % colsplit_c + '#@desc %s\n' % (
                            splitlists[a][b]['description']) + '\n')
                        f.write('#@param separator:"%s"\n' % (splitlists[a][b]['separator']))
                        f.write('#@param removeOriginalColumn:%s\n' % splitlists[a][b]['removeOriginalColumn'])
                        f.write('#@param col-name:%s\n' % splitlists[a][b]['columnName'])
                        f.write('#@in col:%s%d\n' % (columnName, b))
                        dtable_c += 1
                        f.write('#@out table%d\n' % dtable_c)
                        f.write('#@end core/column-split%d\n' % colsplit_c)
                        colsplit_c += 1
                        for k in range(b + 1, innerlenth):
                            if splitlists[a][k]['op'] == 'core/mass-edit':
                                f.write('#@begin core/mass-edit%d' % massedit_c + '#@desc ' + splitlists[a][k][
                                    'description'] + '\n')
                                f.write('#@param col-name:"%s"\n' % splitlists[a][k]['columnName'])
                                ruleforsplitreturn(innerindex, dtable_c, columnName, col_counter)
                                innerindex += 1
                                col_counter += 1
                                f.write('#@end core/mass-edit%d\n' % massedit_c)
                                massedit_c += 1
                            elif splitlists[a][k]['op'] == 'core/text-transform':
                                f.write('#@begin core/text-transform%d' % texttrans_c + '#@desc ' + splitlists[a][k][
                                    'description'] + '\n')
                                f.write('#@param col-name:' + splitlists[a][k]['columnName'] + '\n')
                                f.write('#@param expression:' + splitlists[a][k]['expression'] + '\n')
                                ruleforsplitreturn(innerindex, dtable_c, columnName, col_counter)
                                innerindex += 1
                                col_counter += 1
                                f.write('#@end core/text-transform%d\n' % texttrans_c)
                                texttrans_c += 1
            elif splitlists[a][0]['op'] == 'core/text-transform':
                columnName = splitlists[a][0]['columnName']
                col_counter = 1
                f.write(
                    '#@begin core/text-transform%d' % texttrans_c + '#@desc ' + splitlists[a][0]['description'] + '\n')
                f.write('#@param col-name:' + splitlists[a][0]['columnName'] + '\n')
                f.write('#@param expression:' + splitlists[a][0]['expression'] + '\n')
                f.write('#@in table%d\n' % dtable_c)
                f.write('#@out col:%s%d\n' % (columnName, col_counter))
                texttrans_c += 1
                f.write('#@end core/text-transform%d\n' % texttrans_c)
                for b in range(1, innerlenth):
                    if splitlists[a][b]['op'] == 'core/column-split':
                        innerindex = 0
                        for j in range(1, b):
                            if splitlists[a][j]['op'] == 'core/mass-edit':
                                f.write('#@begin core/mass-edit%d' % massedit_c + '#@desc ' + splitlists[a][j][
                                    'description'] + '\n')
                                f.write('#@param col-name:"%s"\n' % splitlists[a][j]['columnName'])
                                f.write('#@in col:%s%d\n' % (columnName, col_counter))
                                col_counter += 1
                                f.write('#@out col:%s%d\n' % (columnName, col_counter))
                                f.write('#@end core/mass-edit%d\n' % massedit_c)
                                massedit_c += 1
                            elif splitlists[a][j]['op'] == 'core/text-transform':
                                f.write('#@begin core/text-transform%d' % texttrans_c + '#@desc ' + splitlists[a][j][
                                    'description'] + '\n')
                                f.write('#@param col-name:' + splitlists[a][j]['columnName'] + '\n')
                                f.write('#@param expression:' + splitlists[a][j]['expression'] + '\n')
                                f.write('#@in col:%s%d\n' % (columnName, col_counter))
                                col_counter += 1
                                f.write('#@out col:%s%d\n' % (columnName, col_counter))
                                f.write('#@end core/text-transform%d\n' % texttrans_c)
                                texttrans_c += 1
                        f.write('#@begin core/column-split%d' % colsplit_c + '#@desc %s\n' % (
                            splitlists[a][b]['description']) + '\n')
                        f.write('#@param separator:"%s"\n' % (splitlists[a][b]['separator']))
                        f.write('#@param removeOriginalColumn:%s\n' % splitlists[a][b]['removeOriginalColumn'])
                        f.write('#@param col-name:%s\n' % splitlists[a][b]['columnName'])
                        f.write('#@in col:%s%d\n' % (columnName, b))
                        dtable_c += 1
                        f.write('#@out table%d\n' % dtable_c)
                        f.write('#@end core/column-split%d\n' % colsplit_c)
                        colsplit_c += 1
                        for k in range(b + 1, innerlenth):
                            if splitlists[a][k]['op'] == 'core/mass-edit':
                                f.write('#@begin core/mass-edit%d' % massedit_c + '#@desc ' + splitlists[a][k][
                                    'description'] + '\n')
                                f.write('#@param col-name:"%s"\n' % splitlists[a][k]['columnName'])
                                ruleforsplitreturn(innerindex, dtable_c, columnName, col_counter)
                                innerindex += 1
                                col_counter += 1
                                f.write('#@end core/mass-edit%d\n' % massedit_c)
                                massedit_c += 1
                            elif splitlists[a][k]['op'] == 'core/text-transform':
                                f.write('#@begin core/text-transform%d' % texttrans_c + '#@desc ' + splitlists[a][k][
                                    'description'] + '\n')
                                f.write('#@param col-name:' + splitlists[a][k]['columnName'] + '\n')
                                f.write('#@param expression:' + splitlists[a][k]['expression'] + '\n')
                                ruleforsplitreturn(innerindex, dtable_c, columnName, col_counter)
                                innerindex += 1
                                col_counter += 1
                                f.write('#@end core/text-transform%d\n' % texttrans_c)
                                texttrans_c += 1

        f.write('#@begin MergeOperationsColumns #@desc Merge the Parallel Column operations\n')
        for m in range(len(newlist_of_lists)):
            newcol_name = 'col:%s' % (newlist_of_lists[m][0]['columnName'])
            colcounter = len(newlist_of_lists[m])
            f.write('#@in %s%d\n' % (newcol_name, colcounter))

        for n in range(len(splitlists)):
            lenthdicts = len(splitlists[n])
            if splitlists[n][lenthdicts - 1]['op'] == 'core/column-split':
                f.write('#@in table%d\n' % dtable_c)
            else:
                col_c = lenthdicts - 1
                f.write('#@in col:%s%d\n' % (splitlists[n][0]['columnName'], col_c))

        outtable = dtable_c + 1
        f.write('#@out table%d\n' % outtable)
        f.write('#@end MergeOperationsColumns\n')

        f.write('#@end SPOriginalOR2\n')
        output_string = f.getvalue()
        f.close()

        return output_string


if __name__ == '__main__':
    # get projects
    or2yw = OR2YW(server_host="192.168.0.102", server_port="3333")
    projects = or2yw.get_projects()
    print(projects)
    # get operations
    operations = or2yw.get_json("2289658246838")
    print(operations)
    yw_script = or2yw.generate_yw_script(operations["entries"])
    print(yw_script)
    print(OR2YWGenerator.generate_yw_image(yw_script))
