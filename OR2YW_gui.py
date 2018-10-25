import tkFileDialog


from Tkinter import *
from OR2YW import OR2YW
import base64
import tkMessageBox
import os

from subprocess import call


class Application(Frame):
    def createWidgets(self):
        self.grid(row=0, column=0, sticky=N+S+E+W)

        self.label1 = Label(self, text="Open Refine Server:")
        self.label1.grid(row=0,sticky=E)
        self.entry1 = Entry(self)
        self.entry1.grid(row=0, column=1,sticky=E+W)
        self.entry1.insert(0,"http://127.0.0.1:3333")
        self.button1 = Button(self)
        self.button1["text"] = "Check"
        self.button1["command"] = self.check_projects
        self.button1.grid(row=0, column=2,sticky=W)

        def callback_java(sv):
            self._java_loc = sv.get().strip()

        sv1 = StringVar()
        sv1.trace("w", lambda name, index, mode, sv=sv1: callback_java(sv))

        self.label2 = Label(self, text="Java Location:")
        self.label2.grid(row=1,sticky=E)
        self.entry2 = Entry(self,textvariable=sv1)
        self.entry2.grid(row=1, column=1,sticky=E+W)
        self.entry2.insert(0,self._java_loc)
        #self.button2 = Button(self)
        #self.button2["text"] = "Open"
        #self.button2["command"] = self.open_java
        #self.button2.grid(row=1, column=2,sticky=W)

        def callback_dot(sv):
            self._dot_loc = sv.get().strip()

        sv2 = StringVar()
        sv2.trace("w", lambda name, index, mode, sv=sv2: callback_dot(sv))

        self.label3 = Label(self, text="Dot Location:")
        self.label3.grid(row=2, sticky=E)
        self.entry3 = Entry(self,textvariable=sv2)
        self.entry3.grid(row=2, column=1, sticky=E + W)
        self.entry3.insert(0, self._dot_loc)
        #self.button3 = Button(self)
        #self.button3["text"] = "Open"
        #self.button3["command"] = self.open_dot
        #self.button3.grid(row=2, column=2, sticky=W)


        self.listbox_projects = Listbox(self)
        self.listbox_projects.grid(row=3,column=0,columnspan=3,sticky=N+E+W+S)

        self.button4 = Button(self)
        self.button4["text"] = "Generate Workflow"
        self.button4["command"] = self.generate_yw
        self.button4.grid(row=4, column=0,columnspan=3,sticky=E+W)

        #self.image1 = Canvas(self)
        #self.image1.grid(row=1,column=3,sticky=N+E+W+S)


        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)
        self.grid_columnconfigure(3, weight=0)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=1)
        self.grid_rowconfigure(4, weight=0)

    def __init__(self, master=None, java_loc="",dot_loc=""):
        self._java_loc = java_loc
        self._dot_loc = dot_loc
        Frame.__init__(self, master)
        self.or2yw = OR2YW()
        self.pack()
        self.createWidgets()
        self._list_projects = []

    def generate_yw(self):
        #get project
        for x in self.listbox_projects.curselection():
            print(self._list_projects[x])
            url = self.entry1.get()
            url_split = url.split("/")
            address = url_split[2]
            port = address.split(":")
            if len(port) > 1:
                port = port[1]
            else:
                port = 80

            address = address.split(":")[0]

            or2yw = OR2YW(server_host=address, server_port=port)
            json_operations = or2yw.get_json(self._list_projects[x][0])
            print(json_operations)

            yw_script = OR2YW.generate_yw_script(json_operations["entries"])
            print(yw_script)

            if not os.path.isfile(self._java_loc):
                tkMessageBox.showerror("Java Not Found","You must install java to generate the workflow")
                return

            if not os.path.isfile(self._dot_loc):
                tkMessageBox.showerror("Dot Not Found","You must install GraphViz (dot) to generate the workflow")
                return

            encoded_image,file_name = OR2YW.generate_yw_image(yw_script,dot_file=self._dot_loc,java_file=self._java_loc)

            # store to file
            png_filename = tkFileDialog.asksaveasfilename(initialdir=".", title="Select file",
                                                         filetypes=(("png files", "*.png"), ("all files", "*.*")))

            image_bin = base64.decodestring(encoded_image)
            with open(png_filename,"wb") as file:
                file.write(image_bin)
                tkMessageBox.showinfo("Message","Workflow {} saved succesfully".format(self._list_projects[x][1]["name"]))

            """
            print file_name
            window = Tkinter.Tk()
            window.title("Join")
            window.geometry("300x300")
            window.configure(background='grey')


            # Creates a Tkinter-compatible photo image, which can be used everywhere Tkinter expects an image object.
            img = ImageTk.PhotoImage(Image.open(file_name))

            # The Label widget is a standard Tkinter widget used to display a text or image on the screen.
            panel = Tkinter.Label(window, image=img)

            # The Pack geometry manager packs widgets in rows or columns.
            panel.pack(side="bottom", fill="both", expand="yes")
            #img = PhotoImage(data=encoded_image)
            #self.image1.create_image(image=img)
            """

    def check_projects(self):
        #print(self.entry1.get())
        # get the list of projects


        """
        http://0.0.0.0:3333/project?project=2289658246838
        """
        url = self.entry1.get()
        url_split = url.split("/")
        address = url_split[2]
        port = address.split(":")
        if len(port)>1:
            port = port[1]
        else:
            port = 80

        address = address.split(":")[0]

        or2yw = OR2YW(server_host=address,server_port=port)
        projects = or2yw.get_projects()
        self._list_projects = []
        for project,item in projects.items():
            #print(project)
            self.listbox_projects.insert(END, "{}|{}".format(project,item["name"],item["created"]))
            self._list_projects.append((project,item))

        #mainloop()

    def open_java(self):
        init_dir = "/"
        if len(self._java_loc)>0:
            init_dir = self._java_loc
        java_filename = tkFileDialog.askopenfilename(initialdir=init_dir, title="Select Java",
                                                      filetypes=(("png files", "*.png"), ("all files", "*.*")))
        if len(java_filename)>0:
            self._java_loc = java_filename

        self.entry2.insert(0,self._java_loc)

    def open_dot(self):
        init_dir = "/"
        if len(self._dot_loc) > 0:
            init_dir = self._dot_loc
        dot_filename = tkFileDialog.askopenfilename(initialdir=init_dir, title="Select Java",
                                                     filetypes=(("png files", "*.png"), ("all files", "*.*")))
        if len(dot_filename) > 0:
            self._dot_loc = dot_filename

        self.entry3.insert(0, self._dot_loc)

    def open_java(self):
        init_dir = "/"
        if len(self._java_loc)>0:
            init_dir = self._java_loc
        java_filename = tkFileDialog.askopenfilename(initialdir=init_dir, title="Select Java",
                                                      filetypes=(("png files", "*.png"), ("all files", "*.*")))
        if len(java_filename)>0:
            self._java_loc = java_filename

import subprocess
process = subprocess.Popen("which java",shell=True, stdout=subprocess.PIPE)
output = process.stdout.readline()
java_loc = ""
if len(output)>0:
    java_loc = output.strip()
process = subprocess.Popen("which dot",shell=True, stdout=subprocess.PIPE)
output = process.stdout.readline()
dot_loc = ""
if len(output)>0:
    dot_loc = output.strip()


root = Tk()
root.title('Open Refine to Yes Workflow (OR2YW)')
root.geometry('800x600') # Size 200, 200

Grid.rowconfigure(root, 0, weight=1)
Grid.columnconfigure(root, 0, weight=1)
app = Application(master=root,java_loc=java_loc,dot_loc=dot_loc)
app.mainloop()
root.destroy()