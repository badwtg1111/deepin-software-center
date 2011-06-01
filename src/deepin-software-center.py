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

from constant import *
from draw import *
from utils import postGUI
import action
import apt
import apt_pkg
import communityPage
import detailView
import download
import glib
import gtk
import navigatebar
import pango
import pangocairo
import pygtk
import recommendPage
import repoCache
import repositoryPage
import search
import searchPage
import searchUninstallPage as sp
import statusbar
import threading as td
import titlebar
import uninstallPage
import updatePage
import utils
import urllib2
import json
pygtk.require('2.0')

class DeepinSoftwareCenter:
    '''Interface for software center.'''
    DEFAULT_WIDTH = 890
    DEFAULT_HEIGHT = 640
    
    def __init__(self):
        '''Init.'''
        gtk.gdk.threads_init()        
        
        # Shape.
        self.topbarPixbuf = gtk.gdk.pixbuf_new_from_file("./icons/navigate/background.png")
        self.topHeight = self.topbarPixbuf.get_height()
            
        self.bottombarPixbuf = gtk.gdk.pixbuf_new_from_file("./icons/statusbar/background.png")
        self.bottomHeight = self.bottombarPixbuf.get_height()
        
        # Init apt cache.
        apt_pkg.init_config()
        apt_pkg.init_system()
        self.aptCache = apt.Cache()
        self.detailViewDict = {}
        self.searchViewDict = {}
        self.noscreenshotList = []
        
        # Download queue.
        self.downloadQueue = download.DownloadQueue(
            self.downloadUpdateCallback,
            self.downloadFinishCallback,
            self.downloadFailedCallback,
            )
        
        # Action queue.
        self.actionQueue = action.ActionQueue(
            self.actionUpdateCallback,
            self.actionFinishCallback,
            self.actionFailedCallback
            )
        
        # Init widgets.
        self.window = self.initMainWindow()
        self.window.connect("size-allocate", lambda w, a: self.updateShape(w, a))
        self.hasMax = False
        self.leftLine = gtk.Image()
        drawLine(self.leftLine, "#0A3050", 1)
        self.rightLine = gtk.Image()
        drawLine(self.rightLine, "#0A3050", 1)
        self.mainBox = gtk.VBox()
        self.topbox = gtk.VBox()
        self.topbar = gtk.EventBox()
        
        eventBoxSetBackground(
            self.topbar,
            True, False,
            "./icons/navigate/background.png")
        # make window movable or resizable even window is decorated.
        self.topbar.connect('button-press-event', 
                            lambda w, e: utils.moveWindow(w, e, self.window))
        self.topbar.connect("button-press-event", self.doubleClickWindow)
        self.titlebar = titlebar.Titlebar(self.minWindow, self.toggleWindow, self.closeWindow)
        self.navigatebar = navigatebar.NavigateBar()
        self.bodyBox = gtk.HBox()
        self.contentBox = gtk.VBox()
        self.repoCache = repoCache.RepoCache(self.aptCache)
        self.recommendPage = recommendPage.RecommendPage(
            self.repoCache, 
            self.switchStatus,
            self.downloadQueue,
            self.entryDetailView,
            )
        self.repositoryPage = repositoryPage.RepositoryPage(
            self.repoCache, 
            self.switchStatus,
            self.downloadQueue,
            self.entryDetailView,
            self.entrySearchView,
            self.sendVote,
            self.fetchVote,
            )
        self.updatePage = updatePage.UpdatePage(
            self.repoCache, 
            self.switchStatus,
            self.downloadQueue,
            self.entryDetailView,
            self.sendVote,
            self.fetchVote,
            )
        self.uninstallPage = uninstallPage.UninstallPage(
            self.repoCache, 
            self.actionQueue,
            self.entryDetailView,
            self.entrySearchView,
            self.sendVote,
            self.fetchVote,
            )
        self.communityPage = communityPage.CommunityPage()
        # self.morePage = morePage.MorePage()
        self.statusbar = statusbar.Statusbar()
        self.statusbar.eventbox.connect("button-press-event", lambda w, e: utils.resizeWindow(w, e, self.window))
        self.statusbar.eventbox.connect("button-press-event", lambda w, e: utils.moveWindow(w, e, self.window))
        
        self.window.connect_after("show", lambda w: self.createTooltips())
        
    def createTooltips(self):
        '''Create tooltips.'''
        self.tooltips = Tooltips(self.window, self.statusbar.eventbox)    
        
    def message(self, message):
        '''Show message.'''
        self.tooltips.start(message)    
        
    def updateShape(self, widget, allocation):
        '''Update shape.'''
        if allocation.width > 0 and allocation.height > 0:
            width, height = allocation.width, allocation.height
            middleHeight = height - self.topHeight - self.bottomHeight 
            
            topPixbuf = self.topbarPixbuf.scale_simple(width, self.topHeight, gtk.gdk.INTERP_BILINEAR)
            middlePixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, width, middleHeight)
            bottomPixbuf = self.bottombarPixbuf.scale_simple(width, self.bottomHeight, gtk.gdk.INTERP_BILINEAR)
            
            pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, width, height)
            
            topPixbuf.copy_area(0, 0, width, self.topHeight, pixbuf, 0, 0)
            middlePixbuf.copy_area(0, 0, width, middleHeight, pixbuf, 0, self.topHeight)
            bottomPixbuf.copy_area(0, 0, width, self.bottomHeight, pixbuf, 0, self.topHeight + middleHeight)
            
            (_, mask) = pixbuf.render_pixmap_and_mask(255)
            if mask != None:
                self.window.shape_combine_mask(mask, 0, 0)
            
    def switchStatus(self, pkgName, appStatus):
        '''Switch status.'''
        # Update recommand view.
        recommendView = self.recommendPage.recommendView
        recommendView.switchToStatus(pkgName, appStatus)
        
        # Update repo view.
        repoView = self.repositoryPage.repoView
        repoView.switchToStatus(pkgName, appStatus)
        
        # Update application view.
        updateView = self.updatePage.updateView
        updateView.switchToStatus(pkgName, appStatus)
            
        # Update detail view.
        for pageId in [PAGE_RECOMMEND, PAGE_REPO, PAGE_UPGRADE, PAGE_UNINSTALL]:
            if self.detailViewDict.has_key(pageId):
                detailView = self.detailViewDict[pageId]
                detailView.switchToStatus(pkgName, appStatus)
            elif pageId == PAGE_REPO and self.searchViewDict.has_key(pageId):
                searchView = self.searchViewDict[pageId].searchView
                searchView.switchToStatus(pkgName, appStatus)
                
    @postGUI
    def downloadUpdateCallback(self, pkgName, progress, feedback, status=APP_STATE_DOWNLOADING):
        '''Update downloading callback.'''
        if self.repoCache.cache.has_key(pkgName):
            # Update Application information.
            appInfo = self.repoCache.cache[pkgName]
            appInfo.updateDownloadStatus(progress, feedback, status)
            
            # Update recommand view.
            recommendView = self.recommendPage.recommendView
            recommendView.updateDownloadingStatus(pkgName, progress, feedback)
            
            # Update repo view.
            repoView = self.repositoryPage.repoView
            repoView.updateDownloadingStatus(pkgName, progress, feedback)
            
            # Update application view.
            updateView = self.updatePage.updateView
            updateView.updateDownloadingStatus(pkgName, progress, feedback)
            
            # Update detail view.
            for pageId in [PAGE_RECOMMEND, PAGE_REPO, PAGE_UPGRADE, PAGE_UNINSTALL]:
                if self.detailViewDict.has_key(pageId):
                    detailView = self.detailViewDict[pageId]
                    detailView.updateDownloadingStatus(pkgName, progress, feedback)
                elif pageId == PAGE_REPO and self.searchViewDict.has_key(pageId):
                    searchView = self.searchViewDict[pageId].searchView
                    searchView.updateDownloadingStatus(pkgName, progress, feedback)
        else:
            print "Impossible: %s not in RepoCache" % (pkgName)
        
    @postGUI
    def downloadFinishCallback(self, pkgName):
        '''Download finish callback.'''
        if self.repoCache.cache.has_key(pkgName):
            # Update application information.
            appInfo = self.repoCache.cache[pkgName]
            if appInfo.pkg.is_upgradable:
                appStatus = APP_STATE_UPGRADING
            else:
                appStatus = APP_STATE_INSTALLING
            appInfo.switchStatus(appStatus)
                
            # Update application view.
            recommendView = self.recommendPage.recommendView
            recommendView.switchToStatus(pkgName, appStatus)
                
            # Update repo view.
            repoView = self.repositoryPage.repoView
            repoView.switchToStatus(pkgName, appStatus)
                
            # Update update view.
            updateView = self.updatePage.updateView
            updateView.switchToStatus(pkgName, appStatus)
                
            # Update detail view.
            for pageId in [PAGE_RECOMMEND, PAGE_REPO, PAGE_UPGRADE, PAGE_UNINSTALL]:
                if self.detailViewDict.has_key(pageId):
                    detailView = self.detailViewDict[pageId]
                    detailView.switchToStatus(pkgName, appStatus)
                elif pageId == PAGE_REPO and self.searchViewDict.has_key(pageId):
                    searchView = self.searchViewDict[pageId].searchView
                    searchView.switchToStatus(pkgName, appStatus)
                    
            # Require new install action.
            if appStatus == APP_STATE_UPGRADING:
                self.actionQueue.addAction(pkgName, ACTION_UPGRADE)
            else:
                self.actionQueue.addAction(pkgName, ACTION_INSTALL)
        else:
            print "Impossible: %s not in RepoCache" % (pkgName)
            
    @postGUI
    def downloadFailedCallback(self, pkgName):
        '''Download failed callback.'''
        if self.repoCache.cache.has_key(pkgName):
            # Update application information.
            appInfo = self.repoCache.cache[pkgName]
            if appInfo.pkg.is_upgradable:
                appStatus = APP_STATE_UPGRADE
            else:
                appStatus = APP_STATE_NORMAL
            
            # Update application view.
            recommendView = self.recommendPage.recommendView
            recommendView.switchToStatus(pkgName, appStatus)
                
            # Update repo view.
            repoView = self.repositoryPage.repoView
            repoView.switchToStatus(pkgName, appStatus)
                
            # Update update view.
            updateView = self.updatePage.updateView
            updateView.switchToStatus(pkgName, appStatus)
                
            # Update detail view.
            for pageId in [PAGE_RECOMMEND, PAGE_REPO, PAGE_UPGRADE, PAGE_UNINSTALL]:
                if self.detailViewDict.has_key(pageId):
                    detailView = self.detailViewDict[pageId]
                    detailView.switchToStatus(pkgName, appStatus)
                elif pageId == PAGE_REPO and self.searchViewDict.has_key(pageId):
                    searchView = self.searchViewDict[pageId].searchView
                    searchView.switchToStatus(pkgName, appStatus)
        else:
            print "Impossible: %s not in RepoCache" % (pkgName)
            
    @postGUI
    def actionUpdateCallback(self, actionType, pkgName, progress, feedback):
        '''Installing update callback.'''
        if self.repoCache.cache.has_key(pkgName):
            if actionType == ACTION_INSTALL:
                # Update application information.
                appInfo = self.repoCache.cache[pkgName]
                appInfo.updateInstallStatus(progress, feedback)
                
                # Update application view.
                recommendView = self.recommendPage.recommendView
                recommendView.updateInstallingStatus(pkgName, progress, feedback)
                    
                # Update repo view.
                repoView = self.repositoryPage.repoView
                repoView.updateInstallingStatus(pkgName, progress, feedback)
                
                # Update detail view.
                for pageId in [PAGE_RECOMMEND, PAGE_REPO, PAGE_UPGRADE, PAGE_UNINSTALL]:
                    if self.detailViewDict.has_key(pageId):
                        detailView = self.detailViewDict[pageId]
                        detailView.updateInstallingStatus(pkgName, progress, feedback)
                    elif pageId == PAGE_REPO and self.searchViewDict.has_key(pageId):
                        searchView = self.searchViewDict[pageId].searchView
                        searchView.updateInstallingStatus(pkgName, progress, feedback)
            elif actionType == ACTION_UPGRADE:
                # Update application information.
                appInfo = self.repoCache.cache[pkgName]
                appInfo.updateUpgradeStatus(progress, feedback)
                
                # Update application view.
                recommendView = self.recommendPage.recommendView
                recommendView.updateUpgradingStatus(pkgName, progress, feedback)
                    
                # Update repo view.
                repoView = self.repositoryPage.repoView
                repoView.updateUpgradingStatus(pkgName, progress, feedback)
                    
                # Update update view.
                updateView = self.updatePage.updateView
                updateView.updateUpgradingStatus(pkgName, progress, feedback)
                
                # Update detail view.
                for pageId in [PAGE_RECOMMEND, PAGE_REPO, PAGE_UPGRADE, PAGE_UNINSTALL]:
                    if self.detailViewDict.has_key(pageId):
                        detailView = self.detailViewDict[pageId]
                        detailView.updateUpgradingStatus(pkgName, progress, feedback)
                    elif pageId == PAGE_REPO and self.searchViewDict.has_key(pageId):
                        searchView = self.searchViewDict[pageId].searchView
                        searchView.updateUpgradingStatus(pkgName, progress, feedback)
            elif actionType == ACTION_UNINSTALL:
                # Update application information.
                appInfo = self.repoCache.cache[pkgName]
                appInfo.updateUninstallStatus(progress, feedback)
                
                # Update application view.
                uninstallView = self.uninstallPage.uninstallView
                uninstallView.updateUninstallingStatus(pkgName, progress, feedback)
                
                # Update detail view.
                for pageId in [PAGE_RECOMMEND, PAGE_REPO, PAGE_UPGRADE, PAGE_UNINSTALL]:
                    if self.detailViewDict.has_key(pageId):
                        detailView = self.detailViewDict[pageId]
                        detailView.updateUninstallingStatus(pkgName, progress, feedback)
                    elif pageId == PAGE_UNINSTALL and self.searchViewDict.has_key(pageId):
                        searchView = self.searchViewDict[pageId].searchView
                        searchView.updateUninstallingStatus(pkgName, progress, feedback)
        else:
            print "Impossible: %s not in RepoCache" % (pkgName)
            
    @postGUI
    def actionFinishCallback(self, actionType, pkgList):
        '''Installing finish callback.'''
        if actionType == ACTION_INSTALL:
            for (pkgName, isMarkDeleted) in pkgList:
                if self.repoCache.cache.has_key(pkgName):
                    # Update application information.
                    appInfo = self.repoCache.cache[pkgName]
                    if isMarkDeleted:
                        appInfo.switchStatus(APP_STATE_NORMAL)
                    else:
                        appInfo.switchStatus(APP_STATE_INSTALLED)
                
                    # Update recommend view.
                    recommendView = self.recommendPage.recommendView
                    recommendView.initNormalStatus(pkgName, isMarkDeleted)
                    
                    # Update repo view.
                    repoView = self.repositoryPage.repoView
                    repoView.initNormalStatus(pkgName, isMarkDeleted)
                    
                    # Update detail view.
                    for pageId in [PAGE_RECOMMEND, PAGE_REPO, PAGE_UPGRADE, PAGE_UNINSTALL]:
                        if self.detailViewDict.has_key(pageId):
                            detailView = self.detailViewDict[pageId]
                            detailView.initNormalStatus(pkgName, isMarkDeleted)
                        elif pageId == PAGE_REPO and self.searchViewDict.has_key(pageId):
                            searchView = self.searchViewDict[pageId].searchView
                            searchView.initNormalStatus(pkgName, isMarkDeleted)
                        
                    # Add in uninstall list.
                    self.updateUninstallView(pkgName, not isMarkDeleted)
                else:
                    print "Impossible: %s not in RepoCache" % (pkgName)
        elif actionType == ACTION_UPGRADE:
            for (pkgName, isMarkDeleted) in pkgList:
                if self.repoCache.cache.has_key(pkgName):
                    # Update application information.
                    appInfo = self.repoCache.cache[pkgName]
                    if isMarkDeleted:
                        appInfo.switchStatus(APP_STATE_NORMAL)
                    else:
                        appInfo.switchStatus(APP_STATE_INSTALLED)
                        
                        self.repoCache.removePkgFromUpgradableList(pkgName)
                        
                        pkgNum = len(self.repoCache.upgradablePkgs)
                        self.updatePage.topbar.updateNum(pkgNum)
                        
                        updateView = self.updatePage.updateView
                        updateView.update(pkgNum)
                        
                    # Update recommend view.
                    recommendView = self.recommendPage.recommendView
                    recommendView.initNormalStatus(pkgName, isMarkDeleted)
                    
                    # Update repo view.
                    repoView = self.repositoryPage.repoView
                    repoView.initNormalStatus(pkgName, isMarkDeleted)
                    
                    # Update detail view.
                    for pageId in [PAGE_RECOMMEND, PAGE_REPO, PAGE_UPGRADE, PAGE_UNINSTALL]:
                        if self.detailViewDict.has_key(pageId):
                            detailView = self.detailViewDict[pageId]
                            detailView.initNormalStatus(pkgName, isMarkDeleted)
                        elif pageId == PAGE_REPO and self.searchViewDict.has_key(pageId):
                            searchView = self.searchViewDict[pageId].searchView
                            searchView.initNormalStatus(pkgName, isMarkDeleted)
                        
                    # Add in uninstall list.
                    self.updateUninstallView(pkgName, not isMarkDeleted)
                else:
                    print "Impossible: %s not in RepoCache" % (pkgName)
        elif actionType == ACTION_UNINSTALL:
            for (pkgName, isMarkDeleted) in pkgList:
                if self.repoCache.cache.has_key(pkgName):
                    # Update application information.
                    appInfo = self.repoCache.cache[pkgName]
                    appInfo.switchStatus(APP_STATE_NORMAL)
                    
                    self.updateUninstallView(pkgName, False)
                    
                    # Update recommend view.
                    recommendView = self.recommendPage.recommendView
                    recommendView.initNormalStatus(pkgName, isMarkDeleted)
                    
                    # Update repo view.
                    repoView = self.repositoryPage.repoView
                    repoView.initNormalStatus(pkgName, isMarkDeleted)
                    
                    # Update detail view.
                    for pageId in [PAGE_RECOMMEND, PAGE_REPO, PAGE_UPGRADE, PAGE_UNINSTALL]:
                        if self.detailViewDict.has_key(pageId):
                            detailView = self.detailViewDict[pageId]
                            detailView.initNormalStatus(pkgName, isMarkDeleted)
                        elif pageId == PAGE_UNINSTALL and self.searchViewDict.has_key(pageId):
                            searchPage = self.searchViewDict[pageId]
                            searchPage.update(pkgName)
                else:
                    print "Impossible: %s not in RepoCache" % (pkgName)
                    
    @postGUI
    def actionFailedCallback(self, actionType, pkgName):
        '''Installing failed callback.'''
        if actionType == ACTION_INSTALL:
            if self.repoCache.cache.has_key(pkgName):
                # Update application information.
                appInfo = self.repoCache.cache[pkgName]
                appInfo.switchStatus(APP_STATE_NORMAL)
                
                # Update recommend view.
                recommendView = self.recommendPage.recommendView
                recommendView.initNormalStatus(pkgName, True)
                
                # Update repo view.
                repoView = self.repositoryPage.repoView
                repoView.initNormalStatus(pkgName, True)
                
                # Update detail view.
                for pageId in [PAGE_RECOMMEND, PAGE_REPO, PAGE_UPGRADE, PAGE_UNINSTALL]:
                    if self.detailViewDict.has_key(pageId):
                        detailView = self.detailViewDict[pageId]
                        detailView.initNormalStatus(pkgName, True)
                    elif pageId == PAGE_REPO and self.searchViewDict.has_key(pageId):
                        searchView = self.searchViewDict[pageId].searchView
                        searchView.initNormalStatus(pkgName, True)
            else:
                print "Impossible: %s not in RepoCache" % (pkgName)
        elif actionType == ACTION_UPGRADE:
            if self.repoCache.cache.has_key(pkgName):
                # Update application information.
                appInfo = self.repoCache.cache[pkgName]
                appInfo.switchStatus(APP_STATE_UPGRADE)

                # Update recommend view.
                recommendView = self.recommendPage.recommendView
                recommendView.switchToStatus(pkgName, APP_STATE_UPGRADE)
                
                # Update repo view.
                repoView = self.repositoryPage.repoView
                repoView.switchToStatus(pkgName, APP_STATE_UPGRADE)
                
                # Update update view.
                updateView = self.updatePage.updateView
                updateView.switchToStatus(pkgName, APP_STATE_UPGRADE)
                
                # Update detail view.
                for pageId in [PAGE_RECOMMEND, PAGE_REPO, PAGE_UPGRADE, PAGE_UNINSTALL]:
                    if self.detailViewDict.has_key(pageId):
                        detailView = self.detailViewDict[pageId]
                        detailView.switchToStatus(pkgName, APP_STATE_UPGRADE)
                    elif pageId == PAGE_REPO and self.searchViewDict.has_key(pageId):
                        searchView = self.searchViewDict[pageId].searchView
                        searchView.switchToStatus(pkgName, APP_STATE_UPGRADE)
            else:
                print "Impossible: %s not in RepoCache" % (pkgName)
        elif actionType == ACTION_UNINSTALL:
            if self.repoCache.cache.has_key(pkgName):
                # Update application information.
                appInfo = self.repoCache.cache[pkgName]
                appInfo.switchStatus(APP_STATE_INSTALLED)
                
                # Update uninstall view.
                uninstallView = self.uninstallPage.uninstallView
                uninstallView.initUninstallStatus(pkgName)
                
                # Update detail view.
                for pageId in [PAGE_RECOMMEND, PAGE_REPO, PAGE_UPGRADE, PAGE_UNINSTALL]:
                    if self.detailViewDict.has_key(pageId):
                        detailView = self.detailViewDict[pageId]
                        detailView.initNormalStatus(pkgName, False)
                    elif pageId == PAGE_UNINSTALL and self.searchViewDict.has_key(pageId):
                        searchView = self.searchViewDict[pageId].searchView
                        searchView.initUninstallStatus(pkgName)
            else:
                print "Impossible: %s not in RepoCache" % (pkgName)
                
    def updateUninstallView(self, pkgName, isAdd):
        '''Update uninstall view.'''
        if isAdd:
            self.repoCache.addPkgInUninstallableList(pkgName)
        else:
            self.repoCache.removePkgFromUninstallableList(pkgName)

        pkgNum = len(self.repoCache.uninstallablePkgs)
        self.uninstallPage.topbar.updateNum(pkgNum)
        
        uninstallView = self.uninstallPage.uninstallView
        uninstallView.update(pkgNum)
        
    def initMainWindow(self):
        '''Init main window.'''
        # Create main window.
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_decorated(False)
        
        # Init.
        window.set_title('深度Linux软件中心') 
        window.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        (width, height) = utils.getScreenSize(window)
        window.set_default_size(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
        
        # Set icon.
        gtk.window_set_default_icon_from_file("./icons/icon/icon.ico")
            
        return window
    
    def minWindow(self):
        '''Minimum window.'''
        self.window.iconify()     
        
    def doubleClickWindow(self, widget, event):
        '''Handle double click on window.'''
        if utils.isDoubleClick(event):
            self.toggleWindow()
        
    def toggleWindow(self):
        '''Toggle window.'''
        if self.hasMax:
            self.window.unmaximize()
        else:
            self.window.maximize()
            
        self.hasMax = not self.hasMax
        
    def closeWindow(self):
        '''Close window'''
        # Hide window immediately when user click close button,
        # user will feeling this software very quick, ;p
        self.window.hide_all()
        
        self.destroy(self.window)    
        
    def destroy(self, widget, data=None):
        '''Destroy main window.'''
        # Stop download thread.
        if self.downloadQueue.downloadQueue != None:
            self.downloadQueue.downloadQueue.put("STOP")
            
    	gtk.main_quit()
    
    def main(self):
        '''Main'''
        # Connect components.
        self.window.add(self.mainBox)
        self.mainBox.pack_start(self.topbar, False)
        self.topbar.add(self.topbox)
        self.topbox.pack_start(self.titlebar.box, False)
        self.topbox.pack_start(self.navigatebar.box, False)
        self.mainBox.pack_start(self.bodyBox)
        self.bodyBox.pack_start(self.leftLine, False, False)
        self.bodyBox.pack_start(self.contentBox)
        self.bodyBox.pack_start(self.rightLine, False, False)
        
        # Register navigate click event.
        self.navigatebar.recommendIcon.connect(
            "button-press-event", 
            lambda widget, event: self.selectPage(PAGE_RECOMMEND))
        self.navigatebar.repositoryIcon.connect(
            "button-press-event", 
            lambda widget, event: self.selectPage(PAGE_REPO))
        self.navigatebar.updateIcon.connect(
            "button-press-event", 
            lambda widget, event: self.selectPage(PAGE_UPGRADE))
        self.navigatebar.uninstallIcon.connect(
            "button-press-event", 
            lambda widget, event: self.selectPage(PAGE_UNINSTALL))
        self.navigatebar.communityIcon.connect(
            "button-press-event", 
            lambda widget, event: self.selectPage(PAGE_COMMUNITY))
        # self.navigatebar.moreIcon.connect(
        #     "button-press-event", 
        #     lambda widget, event: self.selectPage(PAGE_MORE))
        
        # Default select recommend page.
        self.selectPage(PAGE_RECOMMEND)
        
        # Add statusbar.
        self.mainBox.pack_start(self.statusbar.eventbox, False, False)
        
        # Adjust body box height.
        subCategoryHeight = gtk.gdk.pixbuf_new_from_file("./icons/category/sidebar_normal.png").get_height()
        subCategoryNum = len(self.repoCache.getCategorys())
        self.bodyBox.set_size_request(-1, subCategoryHeight * subCategoryNum)
        
        # Set main window.
        self.window.connect("destroy", self.destroy)
        self.window.show_all()
        
        # Run.
        gtk.main()
        
    def selectPage(self, pageId):
        '''Select recommend page.'''
        utils.containerRemoveAll(self.contentBox)
        
        self.navigatebar.pageId = pageId
        self.navigatebar.box.queue_draw()
        
        if self.detailViewDict.has_key(pageId):
            child = self.detailViewDict[pageId].scrolledWindow
        elif self.searchViewDict.has_key(pageId):
            child = self.searchViewDict[pageId].box
        else:
            if pageId == PAGE_RECOMMEND:
                child = self.recommendPage.scrolledwindow
            elif pageId == PAGE_REPO:
                child = self.repositoryPage.box
            elif pageId == PAGE_UPGRADE:
                child = self.updatePage.box
            elif pageId == PAGE_UNINSTALL:
                child = self.uninstallPage.box
            elif pageId == PAGE_COMMUNITY:
                child = self.communityPage.box
            # else: 
            #     child = self.morePage.box
        
        self.contentBox.pack_start(child)
        self.contentBox.show_all()
                        
    def entryDetailView(self, pageId, appInfo):
        '''Entry detail view.'''
        view = detailView.DetailView(
            self.aptCache, pageId, appInfo, self.switchStatus, self.downloadQueue, self.actionQueue,
            self.exitDetailView, self.noscreenshotList, self.updateMoreComment, self.message)
        self.detailViewDict[pageId] = view
        
        # Fetch detail thread.
        fetchDetailThread = FetchDetail(pageId, utils.getPkgName(appInfo.pkg), self.updateDetailView)
        fetchDetailThread.start()
        
        self.selectPage(pageId)
        
    def sendVote(self, name, vote):
        '''Send vote.'''
        sendVoteThread = SendVote("http://test-linux.gteasy.com/vote.php?n=%s&m=%s" % (name, vote))
        sendVoteThread.start()
        
    def exitDetailView(self, pageId):
        '''Exit detail view.'''
        # Remove detail view first.
        if self.detailViewDict.has_key(pageId):
            self.detailViewDict.pop(pageId)
        
        # Back page.
        self.selectPage(pageId)
        
    def entrySearchView(self, pageId, keyword, pkgList):
        '''Entry search view.'''
        if pageId == PAGE_REPO:
            page = searchPage.SearchPage(
                pageId, self.repoCache, keyword, pkgList,
                self.switchStatus, self.downloadQueue, 
                self.entryDetailView, self.sendVote, self.fetchVote, self.exitSearchView)
        elif pageId == PAGE_UNINSTALL:
            page = sp.SearchUninstallPage(
                pageId, self.repoCache, keyword, pkgList,
                self.actionQueue, 
                self.entryDetailView, self.sendVote, self.fetchVote, self.exitSearchView)
        self.searchViewDict[pageId] = page
        self.selectPage(pageId)
        
    def exitSearchView(self, pageId):
        '''Exit search view.'''
        # Remove search view first.
        if self.searchViewDict.has_key(pageId):
            self.searchViewDict.pop(pageId)
            
        # Select page.
        self.selectPage(pageId)
        
    def fetchVote(self, pageId, appList, isSearchPage=False):
        '''Fetch vote data.'''
        fetchVoteThread = FetchVote(pageId, appList, self.updateVote, isSearchPage)
        fetchVoteThread.start()

    @postGUI
    def updateVote(self, voteJson, pageId, isSearchPage):
        '''Update vote ui.'''
        view = None
        if pageId == PAGE_REPO:
            if isSearchPage:
                if self.searchViewDict.has_key(pageId):
                    view = self.searchViewDict[pageId].searchView
            else:
                view = self.repositoryPage.repoView
                
        elif pageId == PAGE_UPGRADE:
            view = self.updatePage.updateView
        elif pageId == PAGE_UNINSTALL:
            if isSearchPage:
                if self.searchViewDict.has_key(pageId):
                    view = self.searchViewDict[pageId].searchView
            else:
                view = self.uninstallPage.uninstallView
            
        if view != None:
            for vote in voteJson.items():
                # print vote
                (pkgName, [starLevel, voteNum]) = vote
                view.updateVoteView(pkgName, starLevel, voteNum)
    @postGUI
    def updateDetailView(self, pageId, pkgName, voteJson):
        '''Update vote view.'''
        if self.detailViewDict.has_key(pageId):
            detailView = self.detailViewDict[pageId]
            if pkgName == utils.getPkgName(detailView.appInfo.pkg):
                detailView.updateInfo(voteJson)
                
    @postGUI
    def updateMoreComment(self, pageId, pkgName, voteJson):
        '''Update vote view.'''
        if self.detailViewDict.has_key(pageId):
            detailView = self.detailViewDict[pageId]
            if pkgName == utils.getPkgName(detailView.appInfo.pkg):
                detailView.updateMoreComment(voteJson)
        
class FetchVote(td.Thread):
    '''Fetch vote.'''
	
    def __init__(self, pageId, appList, updateVoteCallback, isSearchPage):
        '''Init for fetch vote.'''
        td.Thread.__init__(self)
        self.setDaemon(True) # make thread exit when main program exit 
        
        self.pageId = pageId
        self.isSearchPage = isSearchPage
        self.updateVoteCallback = updateVoteCallback
        
        self.pkgArguments = ""
        for appInfo in appList:
            self.pkgArguments += utils.getPkgName(appInfo.pkg) + ","
        self.pkgArguments = self.pkgArguments.rstrip(",") # remove last , from arguments
        
    def run(self):
        '''Run.'''
        try:
            connection = urllib2.urlopen("http://test-linux.gteasy.com/getMark.php?n=" + self.pkgArguments, timeout=GET_TIMEOUT)
            voteJson = json.loads(connection.read())        
            self.updateVoteCallback(voteJson, self.pageId, self.isSearchPage)
        except Exception, e:
            print "Fetch vote data failed."
        
class SendVote(td.Thread):
    '''Vote'''
	
    def __init__(self, url):
        '''Init for vote.'''
        td.Thread.__init__(self)
        self.setDaemon(True) # make thread exit when main program exit 
        self.url = url

    def run(self):
        '''Run'''
        try:
            post = urllib2.urlopen(self.url, timeout=POST_TIMEOUT)
            print "Post %s successful." % (self.url)
            print "Newest vote: ", post.read()
        except Exception, e:
            print "Post %s failed." % (self.url)
            print "Error: ", e
            
class FetchDetail(td.Thread):
    '''Fetch detail view data.'''
	
    def __init__(self, pageId, pkgName, updateDetailViewCallback):
        '''Init for fetch detail.'''
        td.Thread.__init__(self)
        self.setDaemon(True) # make thread exit when main program exit 
        self.pageId  = pageId
        self.pkgName = pkgName
        self.updateDetailViewCallback = updateDetailViewCallback

    def run(self):
        '''Run'''
        try:
            connection = urllib2.urlopen("http://test-linux.gteasy.com/getComment.php?n=" + self.pkgName, timeout=GET_TIMEOUT)
            voteJson = json.loads(connection.read())        
            self.updateDetailViewCallback(self.pageId, self.pkgName, voteJson)
        except Exception, e:
            print "Fetch detail view data failed."
            
class Tooltips:
    '''Tooltips.'''
    
    def __init__(self, window, widget):
        '''Init for tooltips.'''
        self.width = 300
        self.height = 24
        self.paddingX = 10
        
        self.startTimes = 10
        self.endTimes = 60
        self.times = 70
        self.interval = 80     # in milliseconds
        self.ticker = self.times
        self.message = ""
        
        self.window = gtk.Window()
        self.window.set_decorated(False)
        self.window.set_resizable(True)
        self.window.set_transient_for(window.get_toplevel())
        self.window.set_opacity(0.9)
        self.window.set_property("accept-focus", False)
        
        self.window.set_size_request(self.width, self.height)
        
        self.updatePosition(widget)
        
        window.connect("size-allocate", lambda w, e: self.updatePosition(widget))
        window.connect("configure-event", lambda w, e: self.updatePosition(widget))
        
        self.window.connect("expose-event", self.show)
        
    def start(self, message):
        '''Start.'''
        # Timeout add.
        if self.ticker >= self.times:
            glib.timeout_add(self.interval, self.redraw)
            
        # Init ticker and message.
        self.ticker = 0
        self.message = message
        
    def redraw(self):
        '''Redraw.'''
        if self.ticker >= self.times:
            self.window.hide_all()
            
            return False
        else:
            self.window.show_all()
            
            self.ticker += 1
            self.window.queue_draw()
            
            return True
        
    def show(self, widget, event):
        '''Show'''
        # Draw background.
        rect = widget.allocation
        cr = widget.window.cairo_create()
        cr.set_source_rgb(*colorHexToCairo("#b8d2ff"))
        cr.rectangle(0, 0, rect.width, rect.height)
        cr.fill()
        
        # Draw message.
        fontSize = 16
        drawFont(cr, self.message, fontSize, "#000000",
                 rect.x + self.paddingX, 
                 getFontYCoordinate(rect.y, self.height, fontSize))

        # Change opacity with ticker.
        if self.ticker <= self.startTimes:
            self.window.set_opacity(self.ticker * 0.1)
        elif self.ticker <= self.endTimes:
            self.window.set_opacity(1)
        else:
            self.window.set_opacity((self.times - self.ticker) * 0.1)
        self.window.move(self.x, self.y)
        
        # Expose recursively.
        if widget.get_child() != None:
            widget.propagate_expose(widget.get_child(), event)
            
        return True
        
    def updatePosition(self, widget):
        '''Update position.'''
        (wx, wy) = widget.window.get_origin()
        rect = widget.get_allocation()
        (ww, wh) = (rect.width, rect.height)
        self.x = wx + (ww - self.width) / 2
        self.y = wy - self.height
        
        self.window.queue_draw()
            
if __name__ == "__main__":
    DeepinSoftwareCenter().main()