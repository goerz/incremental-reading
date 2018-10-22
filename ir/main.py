# Copyright 2013 Tiago Barroso
# Copyright 2013 Frank Kmiec
# Copyright 2013-2016 Aleksej
# Copyright 2018 Timothée Chauvin
# Copyright 2017-2018 Joseph Lorimer <luoliyan@posteo.net>
#
# Permission to use, copy, modify, and distribute this software for any purpose
# with or without fee is hereby granted, provided that the above copyright
# notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

from anki.hooks import addHook
from aqt import mw

import sip

from .about import showAbout
from .gui import SettingsDialog
from .settings import SettingsManager
from .text import TextManager
from .util import addMenuItem, isIrCard, loadFile
from .view import ViewManager


class ReadingManager:
    def __init__(self):
        self.textManager = TextManager()
        self.viewManager = ViewManager()
        addHook('profileLoaded', self.onProfileLoaded)
        addHook('overviewStateShortcuts', self.setShortcuts)
        addHook('reviewStateShortcuts', self.setShortcuts)
        addHook('prepareQA', self.onPrepareQA)
        addHook('showAnswer', self.onShowAnswer)
        addHook('reviewCleanup', self.onReviewCleanup)
        self.qshortcuts = []

    def onProfileLoaded(self):
        self.settings = SettingsManager()
        mw.addonManager.setConfigAction(
            __name__, lambda: SettingsDialog(self.settings))
        self.textManager.settings = self.settings
        self.viewManager.settings = self.settings
        self.viewManager.resetZoom('deckBrowser')
        self.addModel()
        self.loadMenuItems()
        self.shortcuts = [
            ('Down', self.viewManager.lineDown),
            ('PgDown', self.viewManager.pageDown),
            ('PgUp', self.viewManager.pageUp),
            ('Up', self.viewManager.lineUp),
            (self.settings['extractKey'], self.textManager.extract),
            (self.settings['highlightKey'], self.textManager.highlight),
            (self.settings['removeKey'], self.textManager.remove),
            (self.settings['undoKey'], self.textManager.undo),
            (self.settings['overlaySeq'], self.textManager.toggleOverlay),
            (self.settings['boldSeq'],
             lambda: self.textManager.format('bold')),
            (self.settings['italicSeq'],
             lambda: self.textManager.format('italic')),
            (self.settings['strikeSeq'],
             lambda: self.textManager.format('strike')),
            (self.settings['underlineSeq'],
             lambda: self.textManager.format('underline')),
        ]

    def loadMenuItems(self):
        if hasattr(mw, 'customMenus') and 'Read' in mw.customMenus:
            mw.customMenus['Read'].clear()

        addMenuItem('Read',
                    'Options...',
                    lambda: SettingsDialog(self.settings),
                    'Alt+1')
        addMenuItem('Read', 'Zoom In', self.viewManager.zoomIn, 'Ctrl++')
        addMenuItem('Read', 'Zoom Out', self.viewManager.zoomOut, 'Ctrl+-')
        addMenuItem('Read', 'About...', showAbout)

        self.settings.loadMenuItems()

    def onPrepareQA(self, html, card, context):
        if isIrCard(card):
            if context == 'reviewQuestion':
                self.qshortcuts = mw.applyShortcuts(self.shortcuts)
                mw.stateShortcuts += self.qshortcuts
        return html

    def onShowAnswer(self):
        for qs in self.qshortcuts:
            mw.stateShortcuts.remove(qs)
            sip.delete(qs)

    def onReviewCleanup(self):
        self.qshortcuts = []

    def setShortcuts(self, shortcuts):
        shortcuts.append(('Ctrl+=', self.viewManager.zoomIn))

    def addModel(self):
        if mw.col.models.byName(self.settings['modelName']):
            return

        model = mw.col.models.new(self.settings['modelName'])
        model['css'] = loadFile('web', 'model.css')

        titleField = mw.col.models.newField(self.settings['titleField'])
        textField = mw.col.models.newField(self.settings['textField'])
        sourceField = mw.col.models.newField(self.settings['sourceField'])
        sourceField['sticky'] = True

        mw.col.models.addField(model, titleField)
        if self.settings['prioEnabled']:
            prioField = mw.col.models.newField(self.settings['priorityField'])
            mw.col.models.addField(model, prioField)

        mw.col.models.addField(model, textField)
        mw.col.models.addField(model, sourceField)

        template = mw.col.models.newTemplate('IR Card')
        template['qfmt'] = '<div class="ir-text">{{%s}}</div>' % (
            self.settings['textField'])

        template['afmt'] = 'When do you want to see this card again?'

        mw.col.models.addTemplate(model, template)
        mw.col.models.add(model)
