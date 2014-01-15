import abc


class SourceBase(metaclass=abc.ABCMeta):
    # OVERRIDE THIS IN YOUR SUBCLASS. If you don't, the program will ignore
    # your plugin.
    pluginid = 'undefined'

    def __init__(self, displaybundle):
        '''Your plugin will be returned a DisplayBundle object. It contains system information like screen resolution.
        You should store this in your plugin when it is initialized.
        '''
        return

    def load_plugin(self):
        '''This method is called after the dependencies for this module are checked. You should import and store any local dependencies 
        from modules that are in your plugin folder. You should create any objects you may need here or store the class if necessary.
        
        The reason this method is here is there will be a feature that if a module this plugin depends on is missing, it can still be instantiated, 
        and further information can be passed to the user on how to fix it. The program may at one point offer a way to download dependencies.
        
        If you are positive that it will load, you can ignore this method and leave it blank, but it is not recommended.
        '''
        return

    @abc.abstractmethod
    def get_images(self):
        '''This method should return a list of URLs.'''
        return

    @abc.abstractmethod
    def get_source_info(self):
        '''This method should return a list containing a human friendly name at index 0, and a human readable url describing the source for this repository.
        For example, the EarthPorn subreddit returns a list ['EarthPorn Subreddit', 'http://reddit.com/r/EarthPorn'].
        This is used to populate the treeview object with your source information.'''
        return

    @abc.abstractmethod
    def get_pluginid(self):
        '''This method should return a string that represents this plugins ID.
        The pluginid is used to make calls to this plugin when necessary. It should be unique as ids are in a shared pool,
        so make sure the id is unique. The id should remain the same even when updated as some settings with the pluginid 
        are persisted by the main application, and they will be lost if the id changes.
        '''
        return

    @abc.abstractmethod
    def get_dependencies(self):
        '''This method should return a list of package names. The host program will check if these packages are available.
        If they are not available, the plugin will be disabled, but the user will be able to elect to install these packages.'''
        return
