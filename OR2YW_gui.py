import Tkinter
from Tkinter import *
import tkFileDialog


from Tkinter import *
from OR2YW import OR2YW
from PIL import ImageTk, Image
import base64

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
        self.listbox_projects = Listbox(self)
        self.listbox_projects.grid(row=1,column=0,columnspan=3,sticky=N+E+W+S)

        self.button2 = Button(self)
        self.button2["text"] = "Generate Workflow"
        self.button2["command"] = self.generate_yw
        self.button2.grid(row=3, column=0,columnspan=3,sticky=E+W)

        #self.image1 = Canvas(self)
        #self.image1.grid(row=1,column=3,sticky=N+E+W+S)


        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)
        self.grid_columnconfigure(3, weight=0)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

    def __init__(self, master=None):
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
            encoded_image,file_name = OR2YW.generate_yw_image(yw_script)

            # store to file
            png_filename = tkFileDialog.asksaveasfilename(initialdir="/", title="Select file",
                                                         filetypes=(("png files", "*.png"), ("all files", "*.*")))

            image_bin = base64.decodestring(encoded_image)
            with open(png_filename,"wb") as file:
                file.write(image_bin)

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


root = Tk()
root.title('Open Refine to Yes Workflow (OR2YW)')
root.geometry('800x600') # Size 200, 200

Grid.rowconfigure(root, 0, weight=1)
Grid.columnconfigure(root, 0, weight=1)
app = Application(master=root)
app.mainloop()
root.destroy()
