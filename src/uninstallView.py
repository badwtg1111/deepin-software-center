#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Author:     Andy Stewart <lazycat.manatee@gmail.com>
# Maintainer: Andy Stewart <lazycat.manatee@gmail.com>
# 
# Copyright (C) 2011 Andy Stewart, all rights reserved.
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from appItem import *
from constant import *
from draw import *
import appView
import gtk
import pango
import pygtk
import utils
pygtk.require('2.0')

class UninstallView(appView.AppView):
    '''Application view.'''
	
    def __init__(self, appNum, getListFunc, actionQueue, 
                 entryDetailCallback, sendVoteCallback, fetchVoteCallback):
        '''Init for application view.'''
        appView.AppView.__init__(self, appNum, PAGE_UNINSTALL)
        
        # Init.
        self.getListFunc = getListFunc
        self.actionQueue = actionQueue
        self.entryDetailCallback = entryDetailCallback
        self.sendVoteCallback = sendVoteCallback
        self.fetchVoteCallback = fetchVoteCallback
        self.itemDict = {}
        
        self.show()
        
    def update(self, appNum):
        '''Update view'''
        self.appNum = appNum
        self.calculateMaxPageIndex()
        self.pageIndex = min(self.pageIndex, self.maxPageIndex)
        self.show(False)

    def createAppList(self, appList):
        '''Create application list.'''
        # Init.
        itemPaddingY = 5
        
        box = gtk.VBox()
        for (index, appInfo) in enumerate(appList):
            appItem = UninstallItem(appInfo, self.actionQueue, 
                                    self.entryDetailCallback, 
                                    self.sendVoteCallback,
                                    index, self.getSelectItemIndex, self.setSelectItemIndex)
            box.pack_start(appItem.itemFrame, False, False)
            self.itemDict[utils.getPkgName(appItem.appInfo.pkg)] = appItem
            
        return box
    
    def initUninstallStatus(self, pkgName):
        '''Init uninstall status.'''
        if self.itemDict.has_key(pkgName):
            appItem = self.itemDict[pkgName]
            appItem.appInfo.status = APP_STATE_INSTALLED
            appItem.confirmUninstall = False
            appItem.initAdditionStatus()