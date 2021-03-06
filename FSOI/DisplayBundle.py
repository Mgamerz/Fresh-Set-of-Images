'''
Created on Jan 12, 2014

@author: Mgamerz
'''


class DisplayBundle:

    '''Contains information that will be passed to all plugins when trying to get images. They might use this
    to limit the images they get.'''

    def __init__(self, screen_width, screen_height):
        self.screen_height = screen_height
        self.screen_width = screen_width

    def get_screen_width(self):
        return self.screen_width

    def get_screen_height(self):
        return self.screen_height

    def __str__(self):
        return 'DisplayBundle Object\nScreen Height:' + str(self.screen_height) + '\nScreen Width:' + str(self.screen_width)
