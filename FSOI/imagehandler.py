'''
@author: Mgamerz
@contact: developer.mgamerzproductions@gmail.com
@license: GPLv3
'''
import threading
import queue
import os
import urllib
import importlib
import re
import SourceBase
import inspect
import importlib.machinery


class imagehandler:
    PLUGINID = 0
    PLUGINSTATUS = 1
    PLUGINOBJ = 2

    def __init__(self, parent):
        self.parent = parent
        self.downloaders = dict()
        self.sourcequeue = queue.Queue()
        self.downloadqueue = queue.Queue()

    def get_images(self, displaybundle):
        # build a list of sites to query based on the treeview object
        sources = self.parent.sources.get_children()
        if sources == None:
            return

        for source in sources:
            if self.parent.sources.item(source, 'values')[0] == 'Yes':
                # source is ready for download.
                print(source)
                self.sourcequeue.put(self.downloaders[str(source)])
        if self.sourcequeue.qsize() <= 0:
            self.parent.status.set('No download sources are enabled.')
            return
        self.parent.downloadButton.config(state='disabled')
        self.parent.status.set('Querying sources for new images...')
        self.parent.progressbar.config(mode='indeterminate')
        self.parent.progressbar.start()
        threading.Thread(target=lambda:
                         self.threadGetImages(displaybundle)).start()

    def threadGetImages(self, displaybundle):
        '''Updates the downloadqueue based on the list of items in the source queue. This runs on a thread that is not the UI thread.'''
        print('Getting images from ' +
              str(self.sourcequeue.qsize()) + ' sources.')
        while self.sourcequeue.qsize():
            try:
                sourceinfo = self.sourcequeue.get(0)
                print(sourceinfo)
                newimages = None
                try:
                    newimages = sourceinfo.get_images(displaybundle)
                except Exception as error:
                    print('Error getting images from',
                          sourceinfo.pluginid, ':', error)
                if newimages:
                    for imageinfo in newimages:
                        # check to make sure image doesn't already exist.
                        if os.path.isfile(self.parent.download_location.get() + imageinfo[1]):
                            print('Validating image', imageinfo[0])
                            print(imageinfo[1] + ' already exists, skipping.')
                            continue
                        self.downloadqueue.put(imageinfo)
            except queue.Empty:
                pass

        # Check to make sure images in the queue are not already on the
        # filesystem. If they are, remove them.
        if self.downloadqueue.qsize() > 0:
            self.downloadImages()
        else:
            self.parent.downloadButton.config(state='enabled')
            self.parent.status.set('No new images to download.')
            self.parent.progressbar.config(mode='determinate')
            self.parent.progress.set(0)
            self.parent.progressbar.stop()

    def downloadImages(self):
        self.parent.progressbar.configure(mode='determinate')
        self.parent.progressbar.stop()
        threading.Thread(target=self.threadDownloadImages).start()

    def threadDownloadImages(self):
        '''Downloads images that were pushed into the download queue. Runs as a thread'''
        tasks = self.downloadqueue.qsize()
        if tasks <= 0:
            return
        taskscompleted = 0
        while self.downloadqueue.qsize():
            try:
                self.parent.updateprogress(taskscompleted, tasks)
                fileinfo = self.downloadqueue.get(0)
                print('Downloading', fileinfo[0])
                urllib.request.urlretrieve(
                    fileinfo[0], self.parent.download_location.get() + fileinfo[1])
                taskscompleted += 1

            except queue.Empty:
                pass
        self.parent.updateprogress(taskscompleted, tasks)
        self.parent.status.set('Images downloaded.')
        self.parent.downloadButton.config(state='enabled')

    def getTreeSources(self):
        '''Gets a list of sources that can be downloaded from.
        This queries our sources folder for .py plugin files with classes that subclass SourceBase and will populate the tree.
        '''

        # This list contains the information that will be injected into the
        # tree.
        sourcesinfo = []
        plugins = self.get_sources()
        for plugin in plugins:
            if plugin[self.PLUGINID] != 'undefined':
                # set all the plugins via this map.
                self.downloaders[plugin[self.PLUGINID]
                                 ] = plugin[self.PLUGINOBJ]
                info = plugin[self.PLUGINOBJ].get_source_info()
                if plugin[self.PLUGINSTATUS] == False:
                    info.insert(0, 'Disabled')  # Put disabled in.
                else:
                    # Empty status - the database of enabled/disabled will set
                    # if this is enabled or disabled at a later stage
                    info.insert(0, '')
                # insert ID as first element.
                info.insert(0, plugin[self.PLUGINID])
                sourcesinfo.append(info)
            else:
                print('Plugin', plugin[0],
                      'does not have the id set, ignoring.')
        return sourcesinfo

    def get_sources(self):
        pluginbase = SourceBase.SourceBase
        # We want to iterate over all modules in  the sources/ directory,
        # allowing the user to make their own.
        classid_map = []
        pluginpath = self.parent.plugin_location.get()
        for root, dirs, files in os.walk(pluginpath):
            candidates = [fname for fname in files if fname.endswith('.py')
                          and not fname.startswith('__')]
            if candidates:
                for c in candidates:
                    modname = os.path.splitext(c)[0]
                    loader = importlib.machinery.SourceFileLoader(
                        modname, root + os.sep + c)
                    module = loader.load_module(modname)

                    # module=__import__(root+'.'+modname, None, None, "*")
                    # #<-- You can get the module this way
                    # <-- Loop over all objects in the module's namespace
                    for cls in dir(module):
                        cls = getattr(module, cls)
                        if (inspect.isclass(cls)  # class we can instantiate
                                and inspect.getmodule(cls) == module  # module
                                and issubclass(cls, pluginbase)):  # Make sure it is a subclass of base
                            plugin = None
                            try:
                                plugin = cls()
                                print('Loading plugin', plugin.pluginid)
                            except TypeError as error:
                                print(
                                    c, 'is not fully defined (or type error occured), cannot fully load plugin:', error)
                                continue
                            except Exception as error:
                                print('{} encountered a fatal error and cannot be loaded.',c)
                            if not self.load_plugin_dependencies(plugin):
                                # add it to the list of plugins. It was able to
                                # load, but we won't enable it, and the user
                                # won't be able to eitehr.
                                classid_map.append(
                                    (cls.pluginid, False, plugin))
                                continue
                            plugin.load_plugin()  # let the plugin loadup
                            # initialize a single object of it. We shouldn't
                            # waste memory making many more of the same
                            # objects.
                            classid_map.append((cls.pluginid, True, plugin))
        return classid_map

    def load_plugin_dependencies(self, plugin):
        dependencies = plugin.get_dependencies()
        for dependency in dependencies:
            try:
                # print(plugin.pluginid,dependency)
                # checking for installed dependency
                importlib.import_module(dependency)
            except ImportError:
                # dependency doesn't exist-check for local version
                print(plugin.pluginid, 'has unmet dependency:',
                      dependency, ', attempting to load from directory.')
                try:
                    # get the listed dependencies filename.
                    loader = importlib.machinery.SourceFileLoader(dependency, os.path.dirname(
                        os.path.abspath(inspect.getfile(plugin.__class__))) + os.sep + dependency + '.py')
                    # if this works, the module will be able to load this
                    # dependency in the load_plugin() method it has.
                    loader.load_module(dependency)
                except (ImportError, FileNotFoundError):
                    print(
                        '%s: No same-folder dependency found. Plugin will partially load but will be disabled.' %
                        plugin.pluginid)
                    return False
        return True

# main
if __name__ == '__main__':
    # main method
    print(
        'ERROR: This file cannot be run on its own. You must use freshsetofimages.py instead.')
