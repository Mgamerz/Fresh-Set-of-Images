'''
Created on Dec 21, 2013
This program is a work in progress and is not yet finished
Requires Python3
@author: Mgamerz
'''
import os
import time
import configparser
import imagehandler
import threading
import sqlite3
from distutils.version import StrictVersion
from datetime import datetime

from tkinter import *
from tkinter import ttk
from tkinter.filedialog import askdirectory

import requests

import DisplayBundle


class FSIGUI:

    def __init__(self):
        self.APP_VERSION = '0.2'
        self.imageutils = imagehandler.imagehandler(self)
        self.setupUI()

    def setupUI(self):
        RIGHTMOUSE = '<Button-3>'
        if sys.platform == 'darwin':
            RIGHTMOUSE = '<Button-2>'
        self.root = Tk()
        self.root.protocol('WM_DELETE_WINDOW', exit)

        # basic properties
        self.progress = IntVar()
        self.status = StringVar()
        self.progress.set(0)
        self.status.set('')
        self.last_doubleclick = 0
        self.prev_doubleclick = None

        self.root.title('Fresh Set of Images')
        self.displaybundle = DisplayBundle.DisplayBundle(
            self.root.winfo_screenwidth(), self.root.winfo_screenheight())

        # tabbed top
        note = ttk.Notebook(self.root)
        note.pack(padx=10, pady=10)

        sourcesframe = ttk.Frame(note)

        self.sources = ttk.Treeview(sourcesframe, columns=(
            'Enabled', 'Name', 'Source'), show='headings', selectmode='browse')
        self.sources.grid(column=0, row=0, columnspan=2,
                          padx=5, pady=5, sticky='NSEW')
        self.sources.bind('<Double-1>', self.OnSourceDoubleClick)
        self.sources.bind(RIGHTMOUSE, self.rightclick_listitem)

        self.sources.tag_configure('enable_color', background='#CCFFCC')
        self.sources.tag_configure('noenable_color', background='#FFCCCC')
        self.sources.tag_configure('disable_color', background='#FF6666')

        self.sources.heading('Enabled', text='Enabled', command=lambda:
                             self.sort_tree(self.sources, 'Enabled', False))
        self.sources.column('Enabled', width=60)
        self.sources.heading('Name', text='Name', command=lambda:
                             self.sort_tree(self.sources, 'Name', False))
        self.sources.heading('Source', text='Source', command=lambda:
                             self.sort_tree(self.sources, 'Source', False))

        # job indicator
        self.textprogress = ttk.Label(sourcesframe, textvariable=self.status)
        self.textprogress.grid(column=0, row=4, padx=5, sticky='W')

        # print(self.displaybundle)

        # download buton
        self.downloadButton = ttk.Button(
            sourcesframe, text='Download Images', command=lambda: self.imageutils.get_images(self.displaybundle))
        self.downloadButton.grid(column=1, row=3, sticky='E', padx=5)

        # progressbar
        self.progressbar = ttk.Progressbar(
            sourcesframe, orient=HORIZONTAL, variable=self.progress, length=160, mode='determinate')
        self.progressbar.grid(column=1, row=4, padx=5, pady=5, sticky='E')

        #--------------------Settings tab-----------------------
        settingsframe = ttk.Frame(note)
        settingsframe.grid(column=0, row=0, sticky='NSEW')

        ttk.Label(settingsframe, text='Download location: ').grid(
            column=0, row=1, padx=5)
        ttk.Label(settingsframe, text='Plugins Folder: ').grid(
            column=0, row=2, padx=5)

        self.download_location = ttk.Entry(settingsframe, width=30)
        self.download_location.grid(column=1, row=1)

        self.plugin_location = ttk.Entry(settingsframe, width=30)
        self.plugin_location.grid(column=1, row=2)

        ttk.Button(settingsframe, text='Browse...',
                   command=self.getDownloadPath).grid(column=2, row=1, padx=5)
        ttk.Button(settingsframe, text='Browse...',
                   command=self.get_plugin_path).grid(column=2, row=2, padx=5)

        self.autocleanup = IntVar()
        self.autocleanup.set(1)
        self.autocleanupcb = ttk.Checkbutton(
            settingsframe, text='Automatically clean up plugin list over time', variable=self.autocleanup)
        self.autocleanupcb.grid(
            column=0, row=3, columnspan=2, sticky='W', padx=5)

        ttk.Button(settingsframe, text='Save', command=self.saveSettings).grid(
            column=2, row=4, sticky='ES')

        #------menubar-------
        menubar = Menu(self.root)

        actionsmenu = Menu(menubar, tearoff=0)
        actionsmenu.add_command(
            label='Reload plugins', command=self.populateTree)

        menubar.add_cascade(menu=actionsmenu, label='Actions')
        self.root.config(menu=menubar)

        # debug
        debugframe = ttk.Frame(note)
        ttk.Button(debugframe, text='Check for updates',
                   command=self.update_check).grid(column=0, row=2)
        ttk.Button(debugframe, text='Print source modules',
                   command=self.imageutils.get_sources).grid(column=0, row=1)

        # add all tabs
        note.add(sourcesframe, text='Sources')
        note.add(settingsframe, text='Settings')
        note.add(debugframe, text='Debugging')

        self.loadSettings()
        self.populateTree()
        self.root.mainloop()
        
    def update_check(self):
        threading.Thread(target=self.updateCheck).start()
        
    def rightclick_listitem(self, event):
        rowitem = self.sources.identify('item', event.x, event.y)

        if rowitem == '':
            print('Right clicked an empty space.')
            return
        # user right clicked something.
        self.sources.selection_set(rowitem)
        rcmenu = Menu(self.root, tearoff=0)
        plugin_disabled=self.sources.item(rowitem, 'values')[0] == 'Disabled'
        if plugin_disabled:
            rcmenu.add_command(label='Plugin is disabled...',
                               command=self.plugin_disabled_click)
        rcmenu.add_command(label='Plugin options', state='disabled' if plugin_disabled else 'active', command=lambda: self.imageutils.plugin_configure(rowitem))
        rcmenu.add_command(label='Uninstall plugin')
        rcmenu.tk_popup(event.x_root, event.y_root)

    def plugin_disabled_click(self):
        PluginDisabledDialog(self.root)


    def get_plugin_path(self):
        startdir = None
        if os.path.isdir(self.download_location.get()):
            startdir = self.plugin_location.get()
        pathdir = askdirectory(initialdir=startdir)
        if pathdir == '':
            return  # cancel
        pathdir = os.path.normpath(pathdir)
        pathdir += os.sep
        self.plugin_location.delete(0, END)
        self.plugin_location.insert(0, pathdir)

    def updateCheck(self):
        print('Checking for updates.')
        '''Fetch an update. Should run on a background thread.'''
        try:
            self.progressbar.config(mode='indeterminate')
            self.progressbar.start()
            
            request = requests.get(
                            'http://freshset.mgamerzproductions.com/versions.ini',headers={'Connection':'close'})
            data = request.content
            data=data.decode(encoding='UTF-8')
            
            config = configparser.ConfigParser()
            config.read_string(data)
            if StrictVersion(self.APP_VERSION) < StrictVersion(config['VERSIONS']['latest']):
                print('Update available online:',
                      config['VERSIONS']['latest'], config['VERSIONS']['url'])

            else:
                
                print('No updates available.')
        except Exception as e:
            print('Error occured checking for updates: {}'.format(e))
            self.progressbar.stop()
            self.progressbar.config(mode='determinate')
            self.progress.set(0)

    def getDownloadPath(self):
        startdir = None
        if os.path.isdir(self.download_location.get()):
            startdir = self.download_location.get()
        pathdir = askdirectory(initialdir=startdir)
        if pathdir == '':
            return  # cancel
        pathdir = os.path.normpath(pathdir)
        pathdir += os.sep
        self.download_location.delete(0, END)
        self.download_location.insert(0, pathdir)

    def OnSourceDoubleClick(self, event):
        millis = int(round(time.time() * 1000))
        item = self.sources.identify('item', event.x, event.y)

        if self.prev_doubleclick == item and millis - self.last_doubleclick < 500:
            # doubleclick was registered in the last 500ms, prevent this so they don't double click twice on a triple click.
            #print('Ignoring previous double click')
            return
        self.last_doubleclick = millis
        # will initialize variable if it hasn't been yet.
        self.prev_doubleclick = item
        vals = list(self.sources.item(item, 'values'))
        if vals:  # check if its not empty
            if vals[0] == 'No':
                vals[0] = 'Yes'
            else:
                if vals[0] == 'Yes':
                    vals[0] = 'No'
            self.sources.item(item, values=vals)
            pluginpath = self.plugin_location.get() #Should eventually put htis in a try block.
            db_file = '{}plugins.db'.format(pluginpath)
            #print(db_file,'doubleclick')
            conn = sqlite3.connect(db_file)
            c = conn.cursor()
            print(item)
            c.execute('INSERT or REPLACE INTO plugin_state VALUES(?,?,?)',(item,vals[0],str(datetime.now())))
            #c.execute('INSERT or REPLACE INTO plugin_state VALUES(\'_fsiplugin_bing\', \'Yes\', \'TODAY\')')
            conn.commit()
            c.close()
            self.update_row_color(item)

    def populateTree(self):
        print('Loading plugins')
        # first delete all items in the tree.
        children = self.sources.get_children()
        if children:
            for child in children:
                self.sources.delete(child)

        treedata = self.imageutils.getTreeSources()
        for source in treedata:
            # DEBUG--REPLACE WITH DATABASE:
            if not source[self.imageutils.PLUGINSTATUS]:
                source[1] = 'Yes'
            id = self.sources.insert('', 'end', source[0], values=source[1:])
            self.update_row_color(id)

        # print(treedata)
    def update_row_color(self, rowid):
        itemvals = self.sources.item(rowid, 'values')
        if itemvals[0] == 'Yes':
            self.sources.item(rowid, tags='enable_color')
        elif itemvals[0] == 'No':
            self.sources.item(rowid, tags='noenable_color')
        elif itemvals[0] == 'Disabled':
            self.sources.item(rowid, tags='disable_color')
        #,tags='installColor' if proginfo[4+presetval]==True else 'noinstallColor')

    def sort_tree(self, tv, col, reverse):
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        l.sort(reverse=reverse)

        # rearrange items in sorted positions
        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)

        # reverse sort next time
        tv.heading(col, command=lambda: self.sort_tree(tv, col, not reverse))

    def updateprogress(self, done, total):
        if done >= total:
            self.status.set('')
            self.progress.set(0)
            return
        increment = 100 / total
        self.progress.set(done * increment)
        self.status.set('Downloading image ' +
                        str(done + 1) + ' of ' + str(total))

    def checkDownloaderFolderSize(self):
        directory_size = 0
        for f in os.listdir(self.download_location):
            if os.path.isfile(f):
                #print(f+", "+str(os.path.getsize(f)))
                directory_size += os.path.getsize(f)
        print('Size of current download folder in megabytes: ' +
              str(directory_size))

    def saveSettings(self):
        if os.path.isdir(self.download_location.get()):
            self.downloadButton.config(state='enabled')
            self.status.set('')
        else:
            self.downloadButton.config(state='disabled')
            self.status.set('Download location is not valid.')
        config = configparser.ConfigParser()
        config['MAIN'] = {'DownloadLocation': self.download_location.get(
        ), 'PluginFolder': self.plugin_location.get(), 'AutoCleanup': self.autocleanup.get()}
        with open('epsettings.ini', 'w') as configfile:
            config.write(configfile)

    def loadSettings(self):
        # default settings
        home = os.path.expanduser("~") + '/Pictures/FreshSet'
        home = os.path.normpath(home)
        if not os.path.isfile('epsettings.ini'):
            print('No config file found.')
            self.downloadButton.config(state='disabled')
            self.status.set('Please configure and save settings for FreshSet.')
            return

        config = configparser.ConfigParser()
        config.read('epsettings.ini')
        self.download_location.delete(0, END)
        self.download_location.insert(0, config['MAIN']['downloadlocation'])
        self.plugin_location.delete(0, END)
        try:
            self.plugin_location.insert(0, config['MAIN']['pluginfolder'])
        except:
            print(
                'pluginfolder config option not defined. Not setting one. No plugins will be loaded.')

        try:
            self.autocleanup.set(config['MAIN']['AutoCleanup'])
        except:
            print('AutoCleanup config option not defined. Defaulting to true.')

        if not os.path.isdir(self.download_location.get()):
            self.downloadButton.config(state='disabled')
            self.status.set('Download location is not valid.')


class PluginDisabledDialog:

    def __init__(self, parent):

        top = self.top = Toplevel(parent)

        ttk.Label(top, text='Plugin Disabled', font=("Purisa", 12)).pack()

        self.e = ttk.Label(
            top, text='Plugin disabled due to unmet dependencies.')
        self.e.pack(padx=5)

        b = Button(top, text="OK", command=self.top.destroy)
        b.pack(pady=5)
# main
if __name__ == '__main__':
    # main method
    FSIGUI()
