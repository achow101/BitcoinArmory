################################################################################
#                                                                              #
# Copyright (C) 2011-2015, Armory Technologies, Inc.                           #
# Distributed under the GNU Affero General Public License (AGPL v3)            #
# See LICENSE or http://www.gnu.org/licenses/agpl.html                         #
#                                                                              #
################################################################################

import math

from PyQt4.Qt import * #@UnusedWildImport
from PyQt4.QtGui import * #@UnusedWildImport

from armoryengine.BDM import TheBDM, BDM_BLOCKCHAIN_READY
from qtdefines import * #@UnusedWildImport
from ui.WalletFrames import AdvancedOptionsFrame

BACKUP_TYPE_135A = '1.35a'
BACKUP_TYPE_135C = '1.35c'
BACKUP_TYPE_0_TEXT = 'Version 0  (from script, 9 lines)'
BACKUP_TYPE_135a_TEXT = 'Version 1.35a (5 lines Unencrypted)'
BACKUP_TYPE_135a_SP_TEXT = u'Version 1.35a (5 lines + SecurePrint\u200b\u2122)'
BACKUP_TYPE_135c_TEXT = 'Version 1.35c (3 lines Unencrypted)'
BACKUP_TYPE_135c_SP_TEXT = u'Version 1.35c (3 lines + SecurePrint\u200b\u2122)'

################################################################################
# Create a special QLineEdit with a masked input
# Forces the cursor to start at position 0 whenever there is no input
class MaskedInputLineEdit(QLineEdit):

   def __init__(self, inputMask):
      super(MaskedInputLineEdit, self).__init__()
      self.setInputMask(inputMask)
      fixFont = GETFONT('Fix', 9)
      self.setFont(fixFont)
      self.setMinimumWidth(tightSizeStr(fixFont, inputMask)[0] + 10)
      self.connect(self, SIGNAL('cursorPositionChanged(int,int)'), self.controlCursor)

   def controlCursor(self, oldpos, newpos):
      if newpos != 0 and len(str(self.text()).strip()) == 0:
         self.setCursorPosition(0)

################################################################################
class DlgUniversalRestoreSelect(ArmoryDialog):

   #############################################################################
   def __init__(self, parent, main):
      super(DlgUniversalRestoreSelect, self).__init__(parent, main)


      lblDescrTitle = QRichLabel(self.tr('<b><u>Restore Wallet from Backup</u></b>'))
      lblDescr = QRichLabel(self.tr('You can restore any kind of backup ever created by Armory using '
         'one of the options below.  If you have a list of private keys '
         'you should open the target wallet and select "Import/Sweep '
         'Private Keys."'))

      self.rdoSingle = QRadioButton(self.tr('Single-Sheet Backup (printed)'))
      self.rdoFragged = QRadioButton(self.tr('Fragmented Backup (incl. mix of paper and files)'))
      self.rdoDigital = QRadioButton(self.tr('Import digital backup or watching-only wallet'))
      self.rdoWOData = QRadioButton(self.tr('Import watching-only wallet data'))
      self.rdoSeed = QRadioButton(self.tr('Import mnemonic seed, Master private key, or Master public key'))
      self.chkTest = QCheckBox(self.tr('This is a test recovery to make sure my backup works'))
      btngrp = QButtonGroup(self)
      btngrp.addButton(self.rdoSingle)
      btngrp.addButton(self.rdoFragged)
      btngrp.addButton(self.rdoDigital)
      btngrp.addButton(self.rdoWOData)
      btngrp.addButton(self.rdoSeed)
      btngrp.setExclusive(True)

      self.rdoSingle.setChecked(True)
      self.connect(self.rdoSingle, SIGNAL(CLICKED), self.clickedRadio)
      self.connect(self.rdoFragged, SIGNAL(CLICKED), self.clickedRadio)
      self.connect(self.rdoDigital, SIGNAL(CLICKED), self.clickedRadio)
      self.connect(self.rdoWOData, SIGNAL(CLICKED), self.clickedRadio)
      self.connect(self.rdoSeed, SIGNAL(CLICKED), self.clickedRadio)


      self.btnOkay = QPushButton(self.tr('Continue'))
      self.btnCancel = QPushButton(self.tr('Cancel'))
      buttonBox = QDialogButtonBox()
      buttonBox.addButton(self.btnOkay, QDialogButtonBox.AcceptRole)
      buttonBox.addButton(self.btnCancel, QDialogButtonBox.RejectRole)
      self.connect(self.btnOkay, SIGNAL(CLICKED), self.clickedOkay)
      self.connect(self.btnCancel, SIGNAL(CLICKED), self.reject)


      layout = QVBoxLayout()
      layout.addWidget(lblDescrTitle)
      layout.addWidget(lblDescr)
      layout.addWidget(HLINE())
      layout.addWidget(self.rdoSingle)
      layout.addWidget(self.rdoFragged)
      layout.addWidget(self.rdoDigital)
      layout.addWidget(self.rdoWOData)
      layout.addWidget(self.rdoSeed)
      layout.addWidget(HLINE())
      layout.addWidget(self.chkTest)
      layout.addWidget(buttonBox)
      self.setLayout(layout)
      self.setMinimumWidth(450)

   def clickedRadio(self):
      if self.rdoDigital.isChecked():
         self.chkTest.setChecked(False)
         self.chkTest.setEnabled(False)
      else:
         self.chkTest.setEnabled(True)

   def clickedOkay(self):
      # ## Test backup option

      doTest = self.chkTest.isChecked()

      if self.rdoSingle.isChecked():
         self.accept()
         dlg = DlgRestoreSingle(self.parent, self.main, doTest)
         if dlg.exec_():
            self.main.addWalletToApplication(dlg.newWallet)
            LOGINFO('Wallet Restore Complete!')

      elif self.rdoFragged.isChecked():
         self.accept()
         dlg = DlgRestoreFragged(self.parent, self.main, doTest)
         if dlg.exec_():
            self.main.addWalletToApplication(dlg.newWallet)
            LOGINFO('Wallet Restore Complete!')
      elif self.rdoDigital.isChecked():
         self.main.execGetImportWltName()
         self.accept()
      elif self.rdoWOData.isChecked():
         # Attempt to restore the root public key & chain code for a wallet.
         # When done, ask for a wallet rescan.
         self.accept()
         dlg = DlgRestoreWOData(self.parent, self.main, doTest)
         if dlg.exec_():
            LOGINFO('Watching-Only Wallet Restore Complete! Will ask for a' \
                    'rescan.')
            self.main.addWalletToApplication(dlg.newWallet)
      elif self.rdoSeed.isChecked():
         # Restore from a BIP 39 seed, Electrum seed, master private key, or master public key
         self.accept()
         dlg = DlgRestoreSeed(self.parent, self.main, doTest)
         if dlg.exec_():
            self.main.addWalletToApplication(dlg.newWallet)
            LOGINFO('Wallet Restore Complete!')
            
################################################################################
class DlgRestoreSeed(ArmoryDialog):
   #############################################################################
   def __init__(self, parent, main, thisIsATest=False, expectWltID=None):
      super(DlgRestoreSeed, self).__init__(parent, main)

      self.thisIsATest = thisIsATest
      self.testWltID = expectWltID
      headerStr = ''
      if thisIsATest:
         lblDescr = QRichLabel(self.tr(
         '<b><u><font color="blue" size="4">Test a Seed or Master key</font></u></b> '
         '<br><br>'
         'Use this window to test a seed or master key backup. '))
      else:
         lblDescr = QRichLabel(self.tr(
         '<b><u>Restore a Wallet from seed or master key</u></b> '
         '<br><br>'
         'Use this window to restore a seed or master key backup.'))


      lblType = QRichLabel(self.tr('<b>Backup Type:</b>'), doWrap=False)

      self.bip39SeedRadio = QRadioButton(self.tr('BIP 39 Seed'), self)
      self.electrumSeedRadio = QRadioButton(self.tr('Electrum seed'), self)
      self.masterPrivkeyRadio = QRadioButton(self.tr('Master Private Key'), self)
      self.masterPubkeyRadio = QRadioButton(self.tr('Master Public Key'), self)
      self.backupTypeButtonGroup = QButtonGroup(self)
      self.backupTypeButtonGroup.addButton(self.bip39SeedRadio)
      self.backupTypeButtonGroup.addButton(self.electrumSeedRadio)
      self.backupTypeButtonGroup.addButton(self.masterPrivkeyRadio)
      self.backupTypeButtonGroup.addButton(self.masterPubkeyRadio)
      self.bip39SeedRadio.setChecked(True)
      self.connect(self.backupTypeButtonGroup, SIGNAL('buttonClicked(int)'), self.changeType)

      layoutRadio = QVBoxLayout()
      layoutRadio.addWidget(self.bip39SeedRadio)
      layoutRadio.addWidget(self.electrumSeedRadio)
      layoutRadio.addWidget(self.masterPrivkeyRadio)
      layoutRadio.addWidget(self.masterPubkeyRadio)
      layoutRadio.setSpacing(0)

      radioButtonFrame = QFrame()
      radioButtonFrame.setLayout(layoutRadio)

      self.derivLineEdit = QLineEdit()
      self.derivationpaths = ['m/44\'/0\'/k\'/i', 'm/0\'\k\'/i\'', 'm/0\'/k/i', '',]
      self.derivLineEdit.setText(self.derivationpaths[0])
      self.derivLineEdit.setReadOnly(True)

      self.cmbPresetDerivs = QComboBox()
      self.cmbPresetDerivs.addItem(self.tr('Default (BIP 44)'))
      self.cmbPresetDerivs.addItem(self.tr('Bitcoin Core'))
      self.cmbPresetDerivs.addItem(self.tr('MultiBit HD'))
      self.cmbPresetDerivs.addItem(self.tr('Custom'))
      self.connect(self.cmbPresetDerivs, SIGNAL('currentIndexChanged(int)'), self.onDerivComboBoxChange)

      layoutDerivPaths = QHBoxLayout()
      layoutDerivPaths.addWidget(self.cmbPresetDerivs)
      layoutDerivPaths.addWidget(self.derivLineEdit)

      cmbFrame = QFrame()
      cmbFrame.setLayout(layoutDerivPaths)

      frmBackupType = makeVertFrame([lblType, radioButtonFrame, cmbFrame])

      frmAllInputs = QFrame()
      frmAllInputs.setFrameStyle(STYLE_RAISED)
      layoutAllInp = QGridLayout()
      layoutAllInp.addWidget(QLabel(self.tr('Seed:')), 0, 0)
      layoutAllInp.addWidget(QLineEdit(), 0, 1)
      frmAllInputs.setLayout(layoutAllInp)

      doItText = self.tr('Test Backup') if thisIsATest else self.tr('Restore Wallet')

      self.btnAccept = QPushButton(doItText)
      self.btnCancel = QPushButton(self.tr("Cancel"))
      self.connect(self.btnAccept, SIGNAL(CLICKED), self.verifyUserInput)
      self.connect(self.btnCancel, SIGNAL(CLICKED), self.reject)
      buttonBox = QDialogButtonBox()
      buttonBox.addButton(self.btnAccept, QDialogButtonBox.AcceptRole)
      buttonBox.addButton(self.btnCancel, QDialogButtonBox.RejectRole)

      self.chkEncrypt = QCheckBox(self.tr('Encrypt Wallet'))
      self.chkEncrypt.setChecked(True)
      bottomFrm = makeHorizFrame([self.chkEncrypt, buttonBox])

      walletRestoreTabs = QTabWidget()
      backupTypeFrame = makeVertFrame([frmBackupType, frmAllInputs])
      walletRestoreTabs.addTab(backupTypeFrame, self.tr("Backup"))
      self.advancedOptionsTab = AdvancedOptionsFrame(parent, main)
      walletRestoreTabs.addTab(self.advancedOptionsTab, self.tr("Advanced Options"))

      layout = QVBoxLayout()
      layout.addWidget(lblDescr)
      layout.addWidget(HLINE())
      layout.addWidget(walletRestoreTabs)
      layout.addWidget(bottomFrm)
      self.setLayout(layout)


      self.chkEncrypt.setChecked(not thisIsATest)
      self.chkEncrypt.setVisible(not thisIsATest)
      self.advancedOptionsTab.setEnabled(not thisIsATest)
      if thisIsATest:
         self.setWindowTitle(self.tr('Test Seed Backup'))
      else:
         self.setWindowTitle(self.tr('Restore Seed Backup'))
         self.connect(self.chkEncrypt, SIGNAL(CLICKED), self.onEncryptCheckboxChange)

      self.setMinimumWidth(500)
      self.layout().setSizeConstraint(QLayout.SetFixedSize)
      self.changeType(self.backupTypeButtonGroup.checkedId())

   #############################################################################
   # Change derivation path when changed
   def onDerivComboBoxChange(self, index):
      self.derivLineEdit.setText(self.derivationpaths[index])
      if index != 3:
         self.derivLineEdit.setReadOnly(True)
      else:
         self.derivLineEdit.setReadOnly(False)

   #############################################################################
   # Hide advanced options whenver the restored wallet is unencrypted
   def onEncryptCheckboxChange(self):
      self.advancedOptionsTab.setEnabled(self.chkEncrypt.isChecked())

   #############################################################################
   def changeType(self, sel):
      if   sel == self.backupTypeButtonGroup.id(self.bip39SeedRadio):
         visList = [0, 1, 1, 1, 1]
      elif sel == self.backupTypeButtonGroup.id(self.electrumSeedRadio):
         visList = [0, 1, 1, 1, 1]
      elif sel == self.backupTypeButtonGroup.id(self.masterPrivkeyRadio):
         visList = [1, 1, 1, 1, 1]
      elif sel == self.backupTypeButtonGroup.id(self.masterPubkeyRadio):
         visList = [0, 1, 1, 0, 0]
      else:
         LOGERROR('What the heck backup type is selected?  %d', sel)
         return

   #############################################################################
   def verifyUserInput(self):
      nError = 0
      seedOrKeySTr = self.edtList[0].text()
      derivationPath = self.edtList[1].text()
      inputData = []
      isSeed = " " in data
      if isSeed:
         # Check BIP 39 seed
         if self.bip39SeedRadio.isChecked():
            # TODO: Check this
            pass
         elif self.electrumSeedRadio.isChecked():
            # TODO: Check this
            pass
         elif self.masterPrivkeyRadio.isChecked():
            # TODO: Check this
            pass
         elif self.masterPubkeyRadio.isChecked():
            # TODO: Check this
            pass

      if self.chkEncrypt.isChecked() and self.advancedOptionsTab.getKdfSec() == -1:
            QMessageBox.critical(self, self.tr('Invalid Target Compute Time'), \
               self.tr('You entered Target Compute Time incorrectly.\n\nEnter: <Number> (ms, s)'), QMessageBox.Ok)
            return
      if self.chkEncrypt.isChecked() and self.advancedOptionsTab.getKdfBytes() == -1:
            QMessageBox.critical(self, self.tr('Invalid Max Memory Usage'), \
               self.tr('You entered Max Memory Usage incorrectly.\n\nEnter: <Number> (kB, MB)'), QMessageBox.Ok)
            return
      if nError > 0:
         pluralStr = 'error' if nError == 1 else 'errors'

         msg = self.tr(
            'Detected errors in the data you entered. '
            'Armory attempted to fix the errors but it is not '
            'always right.  Be sure to verify the "Wallet Unique ID" '
            'closely on the next window.')

         QMessageBox.question(self, self.tr('Errors Corrected'), msg, \
            QMessageBox.Ok)

      # Stop here if this was just a test
      if self.thisIsATest:
         return

      passwd = []
      if self.chkEncrypt.isChecked():
         dlgPasswd = DlgChangePassphrase(self, self.main)
         if dlgPasswd.exec_():
            passwd = SecureBinaryData(str(dlgPasswd.edtPasswd1.text()))
         else:
            QMessageBox.critical(self, self.tr('Cannot Encrypt'), \
               self.tr('You requested your restored wallet be encrypted, but no '
               'valid passphrase was supplied.  Aborting wallet recovery.'), \
               QMessageBox.Ok)
            return

      shortl = ''
      longl  = ''
      nPool  = 1000
      
      # TODO: Make the wallet and add the stuff to it. Requires BIP 32 wallets for this

      self.accept()



################################################################################
class DlgRestoreSingle(ArmoryDialog):
   #############################################################################
   def __init__(self, parent, main, thisIsATest=False, expectWltID=None):
      super(DlgRestoreSingle, self).__init__(parent, main)

      self.thisIsATest = thisIsATest
      self.testWltID = expectWltID
      headerStr = ''
      if thisIsATest:
         lblDescr = QRichLabel(self.tr(
         '<b><u><font color="blue" size="4">Test a Paper Backup</font></u></b> '
         '<br><br>'
         'Use this window to test a single-sheet paper backup.  If your '
         'backup includes imported keys, those will not be covered by this test.'))
      else:
         lblDescr = QRichLabel(self.tr(
         '<b><u>Restore a Wallet from Paper Backup</u></b> '
         '<br><br>'
         'Use this window to restore a single-sheet paper backup. '
         'If your backup includes extra pages with '
         'imported keys, please restore the base wallet first, then '
         'double-click the restored wallet and select "Import Private '
         'Keys" from the right-hand menu.'))


      lblType = QRichLabel(self.tr('<b>Backup Type:</b>'), doWrap=False)

      self.version135Button = QRadioButton(self.tr('Version 1.35 (4 lines)'), self)
      self.version135aButton = QRadioButton(self.tr('Version 1.35a (4 lines Unencrypted)'), self)
      self.version135aSPButton = QRadioButton(self.trUtf8(u'Version 1.35a (4 lines + SecurePrint\u200b\u2122)'), self)
      self.version135cButton = QRadioButton(self.tr('Version 1.35c (2 lines Unencrypted)'), self)
      self.version135cSPButton = QRadioButton(self.trUtf8(u'Version 1.35c (2 lines + SecurePrint\u200b\u2122)'), self)
      self.backupTypeButtonGroup = QButtonGroup(self)
      self.backupTypeButtonGroup.addButton(self.version135Button)
      self.backupTypeButtonGroup.addButton(self.version135aButton)
      self.backupTypeButtonGroup.addButton(self.version135aSPButton)
      self.backupTypeButtonGroup.addButton(self.version135cButton)
      self.backupTypeButtonGroup.addButton(self.version135cSPButton)
      self.version135cButton.setChecked(True)
      self.connect(self.backupTypeButtonGroup, SIGNAL('buttonClicked(int)'), self.changeType)

      layoutRadio = QVBoxLayout()
      layoutRadio.addWidget(self.version135Button)
      layoutRadio.addWidget(self.version135aButton)
      layoutRadio.addWidget(self.version135aSPButton)
      layoutRadio.addWidget(self.version135cButton)
      layoutRadio.addWidget(self.version135cSPButton)
      layoutRadio.setSpacing(0)

      radioButtonFrame = QFrame()
      radioButtonFrame.setLayout(layoutRadio)

      frmBackupType = makeVertFrame([lblType, radioButtonFrame])

      self.lblSP = QRichLabel(self.trUtf8(u'SecurePrint\u200b\u2122 Code:'), doWrap=False)
      self.editSecurePrint = QLineEdit()
      self.prfxList = [QLabel(self.tr('Root Key:')), QLabel(''), QLabel(self.tr('Chaincode:')), QLabel('')]

      inpMask = '<AAAA\ AAAA\ AAAA\ AAAA\ \ AAAA\ AAAA\ AAAA\ AAAA\ \ AAAA!'
      self.edtList = [MaskedInputLineEdit(inpMask) for i in range(4)]


      self.frmSP = makeHorizFrame([STRETCH, self.lblSP, self.editSecurePrint])

      frmAllInputs = QFrame()
      frmAllInputs.setFrameStyle(STYLE_RAISED)
      layoutAllInp = QGridLayout()
      layoutAllInp.addWidget(self.frmSP, 0, 0, 1, 2)
      for i in range(4):
         layoutAllInp.addWidget(self.prfxList[i], i + 1, 0)
         layoutAllInp.addWidget(self.edtList[i], i + 1, 1)
      frmAllInputs.setLayout(layoutAllInp)

      doItText = self.tr('Test Backup') if thisIsATest else self.tr('Restore Wallet')

      self.btnAccept = QPushButton(doItText)
      self.btnCancel = QPushButton(self.tr("Cancel"))
      self.connect(self.btnAccept, SIGNAL(CLICKED), self.verifyUserInput)
      self.connect(self.btnCancel, SIGNAL(CLICKED), self.reject)
      buttonBox = QDialogButtonBox()
      buttonBox.addButton(self.btnAccept, QDialogButtonBox.AcceptRole)
      buttonBox.addButton(self.btnCancel, QDialogButtonBox.RejectRole)

      self.chkEncrypt = QCheckBox(self.tr('Encrypt Wallet'))
      self.chkEncrypt.setChecked(True)
      bottomFrm = makeHorizFrame([self.chkEncrypt, buttonBox])

      walletRestoreTabs = QTabWidget()
      backupTypeFrame = makeVertFrame([frmBackupType, frmAllInputs])
      walletRestoreTabs.addTab(backupTypeFrame, self.tr("Backup"))
      self.advancedOptionsTab = AdvancedOptionsFrame(parent, main)
      walletRestoreTabs.addTab(self.advancedOptionsTab, self.tr("Advanced Options"))

      layout = QVBoxLayout()
      layout.addWidget(lblDescr)
      layout.addWidget(HLINE())
      layout.addWidget(walletRestoreTabs)
      layout.addWidget(bottomFrm)
      self.setLayout(layout)


      self.chkEncrypt.setChecked(not thisIsATest)
      self.chkEncrypt.setVisible(not thisIsATest)
      self.advancedOptionsTab.setEnabled(not thisIsATest)
      if thisIsATest:
         self.setWindowTitle(self.tr('Test Single-Sheet Backup'))
      else:
         self.setWindowTitle(self.tr('Restore Single-Sheet Backup'))
         self.connect(self.chkEncrypt, SIGNAL(CLICKED), self.onEncryptCheckboxChange)

      self.setMinimumWidth(500)
      self.layout().setSizeConstraint(QLayout.SetFixedSize)
      self.changeType(self.backupTypeButtonGroup.checkedId())

   #############################################################################
   # Hide advanced options whenver the restored wallet is unencrypted
   def onEncryptCheckboxChange(self):
      self.advancedOptionsTab.setEnabled(self.chkEncrypt.isChecked())

   #############################################################################
   def changeType(self, sel):
      if   sel == self.backupTypeButtonGroup.id(self.version135Button):
         visList = [0, 1, 1, 1, 1]
      elif sel == self.backupTypeButtonGroup.id(self.version135aButton):
         visList = [0, 1, 1, 1, 1]
      elif sel == self.backupTypeButtonGroup.id(self.version135aSPButton):
         visList = [1, 1, 1, 1, 1]
      elif sel == self.backupTypeButtonGroup.id(self.version135cButton):
         visList = [0, 1, 1, 0, 0]
      elif sel == self.backupTypeButtonGroup.id(self.version135cSPButton):
         visList = [1, 1, 1, 0, 0]
      else:
         LOGERROR('What the heck backup type is selected?  %d', sel)
         return

      self.doMask = (visList[0] == 1)
      self.frmSP.setVisible(self.doMask)
      for i in range(4):
         self.prfxList[i].setVisible(visList[i + 1] == 1)
         self.edtList[ i].setVisible(visList[i + 1] == 1)

      self.isLongForm = (visList[-1] == 1)


   #############################################################################
   def verifyUserInput(self):
      inputLines = []
      nError = 0
      rawBin = None
      nLine = 4 if self.isLongForm else 2
      for i in range(nLine):
         hasError = False
         try:
            rawEntry = str(self.edtList[i].text())
            rawBin, err = readSixteenEasyBytes(rawEntry.replace(' ', ''))
            if err == 'Error_2+':
               hasError = True
            elif err == 'Fixed_1':
               nError += 1
         except:
            hasError = True

         if hasError:
            lineNumber = i+1
            reply = QMessageBox.critical(self, self.tr('Invalid Data'), self.tr(
               'There is an error in the data you entered that could not be '
               'fixed automatically.  Please double-check that you entered the '
               'text exactly as it appears on the wallet-backup page.  <br><br> '
               'The error occured on <font color="red">line #%1</font>.').arg(lineNumber), \
               QMessageBox.Ok)
            LOGERROR('Error in wallet restore field')
            self.prfxList[i].setText('<font color="red">' + str(self.prfxList[i].text()) + '</font>')
            return

         inputLines.append(rawBin)

      if self.chkEncrypt.isChecked() and self.advancedOptionsTab.getKdfSec() == -1:
            QMessageBox.critical(self, self.tr('Invalid Target Compute Time'), \
               self.tr('You entered Target Compute Time incorrectly.\n\nEnter: <Number> (ms, s)'), QMessageBox.Ok)
            return
      if self.chkEncrypt.isChecked() and self.advancedOptionsTab.getKdfBytes() == -1:
            QMessageBox.critical(self, self.tr('Invalid Max Memory Usage'), \
               self.tr('You entered Max Memory Usage incorrectly.\n\nEnter: <Number> (kB, MB)'), QMessageBox.Ok)
            return
      if nError > 0:
         pluralStr = 'error' if nError == 1 else 'errors'

         msg = self.tr(
            'Detected errors in the data you entered. '
            'Armory attempted to fix the errors but it is not '
            'always right.  Be sure to verify the "Wallet Unique ID" '
            'closely on the next window.')

         QMessageBox.question(self, self.tr('Errors Corrected'), msg, \
            QMessageBox.Ok)

      privKey = SecureBinaryData(''.join(inputLines[:2]))
      if self.isLongForm:
         chain = SecureBinaryData(''.join(inputLines[2:]))



      if self.doMask:
         # Prepare the key mask parameters
         SECPRINT = HardcodedKeyMaskParams()
         securePrintCode = str(self.editSecurePrint.text()).strip()
         if not checkSecurePrintCode(self, SECPRINT, securePrintCode):
            return


         maskKey = SECPRINT['FUNC_KDF'](securePrintCode)
         privKey = SECPRINT['FUNC_UNMASK'](privKey, ekey=maskKey)
         if self.isLongForm:
            chain = SECPRINT['FUNC_UNMASK'](chain, ekey=maskKey)

      if not self.isLongForm:
         chain = DeriveChaincodeFromRootKey(privKey)

      # If we got here, the data is valid, let's create the wallet and accept the dlg
      # Now we should have a fully-plaintext rootkey and chaincode
      root = PyBtcAddress().createFromPlainKeyData(privKey)
      root.chaincode = chain

      first = root.extendAddressChain()
      newWltID = binary_to_base58((ADDRBYTE + first.getAddr160()[:5])[::-1])

      # Stop here if this was just a test
      if self.thisIsATest:
         verifyRecoveryTestID(self, newWltID, self.testWltID)
         return

      dlgOwnWlt = None
      if self.main.walletMap.has_key(newWltID):
         dlgOwnWlt = DlgReplaceWallet(newWltID, self.parent, self.main)

         if (dlgOwnWlt.exec_()):
            if dlgOwnWlt.output == 0:
               return
         else:
            self.reject()
            return
      else:
         reply = QMessageBox.question(self, self.tr('Verify Wallet ID'), \
                  self.tr('The data you entered corresponds to a wallet with a wallet ID: \n\n'
                  '%1\n\nDoes this ID match the "Wallet Unique ID" '
                  'printed on your paper backup?  If not, click "No" and reenter '
                  'key and chain-code data again.').arg(newWltID), \
                  QMessageBox.Yes | QMessageBox.No)
         if reply == QMessageBox.No:
            return

      passwd = []
      if self.chkEncrypt.isChecked():
         dlgPasswd = DlgChangePassphrase(self, self.main)
         if dlgPasswd.exec_():
            passwd = SecureBinaryData(str(dlgPasswd.edtPasswd1.text()))
         else:
            QMessageBox.critical(self, self.tr('Cannot Encrypt'), \
               self.tr('You requested your restored wallet be encrypted, but no '
               'valid passphrase was supplied.  Aborting wallet recovery.'), \
               QMessageBox.Ok)
            return

      shortl = ''
      longl  = ''
      nPool  = 1000

      if dlgOwnWlt is not None:
         if dlgOwnWlt.Meta is not None:
            shortl = ' - %s' % (dlgOwnWlt.Meta['shortLabel'])
            longl  = dlgOwnWlt.Meta['longLabel']
            nPool = max(nPool, dlgOwnWlt.Meta['naddress'])

      self.newWallet = PyBtcWallet()

      if passwd:
         self.newWallet.createNewWallet( \
                                 plainRootKey=privKey, \
                                 chaincode=chain, \
                                 shortLabel='Restored - ' + newWltID +shortl, \
                                 longLabel=longl, \
                                 withEncrypt=True, \
                                 securePassphrase=passwd, \
                                 kdfTargSec = \
                                 self.advancedOptionsTab.getKdfSec(), \
                                 kdfMaxMem = \
                                 self.advancedOptionsTab.getKdfBytes(),
                                 isActuallyNew=False, \
                                 doRegisterWithBDM=False)
      else:
         self.newWallet.createNewWallet( \
                                 plainRootKey=privKey, \
                                 chaincode=chain, \
                                 shortLabel='Restored - ' + newWltID +shortl, \
                                 longLabel=longl, \
                                 withEncrypt=False, \
                                 isActuallyNew=False, \
                                 doRegisterWithBDM=False)

      fillAddrPoolProgress = DlgProgress(self, self.main, HBar=1,
                                         Title=self.tr("Computing New Addresses"))
      fillAddrPoolProgress.exec_(self.newWallet.fillAddressPool, nPool)

      if dlgOwnWlt is not None:
         if dlgOwnWlt.Meta is not None:
            from armoryengine.PyBtcWallet import WLT_UPDATE_ADD
            for n_cmt in range(0, dlgOwnWlt.Meta['ncomments']):
               entrylist = []
               entrylist = list(dlgOwnWlt.Meta[n_cmt])
               self.newWallet.walletFileSafeUpdate([[WLT_UPDATE_ADD,
                                                     entrylist[2],
                                                     entrylist[1],
                                                     entrylist[0]]])

         self.newWallet = PyBtcWallet().readWalletFile(self.newWallet.walletPath)
      self.accept()


# Class that will create the watch-only wallet data (root public key & chain
# code) restoration window.
################################################################################
class DlgRestoreWOData(ArmoryDialog):
   #############################################################################
   def __init__(self, parent, main, thisIsATest=False, expectWltID=None):
      super(DlgRestoreWOData, self).__init__(parent, main)

      self.thisIsATest = thisIsATest
      self.testWltID = expectWltID
      headerStr = ''
      lblDescr = ''

      # Write the text at the top of the window.
      if thisIsATest:
         lblDescr = QRichLabel(self.tr(
         '<b><u><font color="blue" size="4">Test a Watch-Only Wallet Restore '
         '</font></u></b><br><br>'
         'Use this window to test the restoration of a watch-only wallet using '
         'the wallet\'s data. You can either type the data on a root data '
         'printout or import the data from a file.'))
      else:
         lblDescr = QRichLabel(self.tr(
         '<b><u><font color="blue" size="4">Restore a Watch-Only Wallet '
         '</font></u></b><br><br>'
         'Use this window to restore a watch-only wallet using the wallet\'s '
         'data. You can either type the data on a root data printout or import '
         'the data from a file.'))

      # Create the line that will contain the imported ID.
      self.rootIDLabel = QRichLabel(self.tr('Watch-Only Root ID:'), doWrap=False)
      inpMask = '<AAAA\ AAAA\ AAAA\ AAAA\ AA!'
      self.rootIDLine = MaskedInputLineEdit(inpMask)
      self.rootIDLine.setFont(GETFONT('Fixed', 9))
      self.rootIDFrame = makeHorizFrame([STRETCH, self.rootIDLabel, \
                                         self.rootIDLine])

      # Create the lines that will contain the imported key/code data.
      self.pkccLList = [QLabel(self.tr('Data:')), QLabel(''), QLabel(''), QLabel('')]
      for y in self.pkccLList:
         y.setFont(GETFONT('Fixed', 9))
      inpMask = '<AAAA\ AAAA\ AAAA\ AAAA\ \ AAAA\ AAAA\ AAAA\ AAAA\ \ AAAA!'
      self.pkccList = [MaskedInputLineEdit(inpMask) for i in range(4)]
      for x in self.pkccList:
         x.setFont(GETFONT('Fixed', 9))

      # Build the frame that will contain both the ID and the key/code data.
      frmAllInputs = QFrame()
      frmAllInputs.setFrameStyle(STYLE_RAISED)
      layoutAllInp = QGridLayout()
      layoutAllInp.addWidget(self.rootIDFrame, 0, 0, 1, 2)
      for i in range(4):
         layoutAllInp.addWidget(self.pkccLList[i], i + 1, 0)
         layoutAllInp.addWidget(self.pkccList[i], i + 1, 1)
      frmAllInputs.setLayout(layoutAllInp)

      # Put together the button code.
      doItText = self.tr('Test Backup') if thisIsATest else self.tr('Restore Wallet')
      self.btnLoad   = QPushButton(self.tr("Load From Text File"))
      self.btnAccept = QPushButton(doItText)
      self.btnCancel = QPushButton(self.tr("Cancel"))
      self.connect(self.btnLoad, SIGNAL(CLICKED), self.loadWODataFile)
      self.connect(self.btnAccept, SIGNAL(CLICKED), self.verifyUserInput)
      self.connect(self.btnCancel, SIGNAL(CLICKED), self.reject)
      buttonBox = QDialogButtonBox()
      buttonBox.addButton(self.btnLoad, QDialogButtonBox.AcceptRole)
      buttonBox.addButton(self.btnAccept, QDialogButtonBox.AcceptRole)
      buttonBox.addButton(self.btnCancel, QDialogButtonBox.RejectRole)

      # Set the final window layout.
      finalLayout = QVBoxLayout()
      finalLayout.addWidget(lblDescr)
      finalLayout.addWidget(makeHorizFrame(['Stretch',self.btnLoad]))
      finalLayout.addWidget(HLINE())
      finalLayout.addWidget(frmAllInputs)
      finalLayout.addWidget(makeHorizFrame([self.btnCancel, 'Stretch', self.btnAccept]))
      finalLayout.setStretch(0, 0)
      finalLayout.setStretch(1, 0)
      finalLayout.setStretch(2, 0)
      finalLayout.setStretch(3, 0)
      finalLayout.setStretch(4, 0)
      finalLayout.setStretch(4, 1)
      finalLayout.setStretch(4, 2)
      self.setLayout(finalLayout)

      # Set window title.
      if thisIsATest:
         self.setWindowTitle(self.tr('Test Watch-Only Wallet Backup'))
      else:
         self.setWindowTitle(self.tr('Restore Watch-Only Wallet Backup'))

      # Set final window layout options.
      self.setMinimumWidth(550)
      self.layout().setSizeConstraint(QLayout.SetFixedSize)


   #############################################################################
   def loadWODataFile(self):
      '''Function for loading a root public key/chain code (\"pkcc\") file.'''
      fn = self.main.getFileLoad(self.tr('Import Wallet File'),
                                 ffilter=[self.tr('Root Pubkey Text Files (*.rootpubkey)')])
      if not os.path.exists(fn):
         return

      # Read in the data.
      # Protip: readlines() leaves in '\n'. read().splitlines() nukes '\n'.
      loadFile = open(fn, 'rb')
      fileLines = loadFile.read().splitlines()
      loadFile.close()

      # Confirm that we have an actual PKCC file.
      pkccFileVer = int(fileLines[0], 10)
      if pkccFileVer != 1:
         return
      else:
         self.rootIDLine.setText(QString(fileLines[1]))
         for curLineNum, curLine in enumerate(fileLines[2:6]):
            self.pkccList[curLineNum].setText(QString(curLine))


   #############################################################################
   def verifyUserInput(self):
      '''Function that verifies the input for a root public key/chain code
         restoration validation.'''
      inRootChecked = ''
      inputLines = []
      nError = 0
      rawBin = None
      nLine = 4
      hasError = False

      # Read in the root ID data and handle any errors.
      try:
         rawID = easyType16_to_binary(str(self.rootIDLine.text()).replace(' ', ''))
         if len(rawID) != 9:
            raise ValueError('Must supply 9 byte input for the ID')

         # Grab the data and apply the checksum to make sure it's okay.
         inRootData = rawID[:7]   # 7 bytes
         inRootChksum = rawID[7:] # 2 bytes
         inRootChecked = verifyChecksum(inRootData, inRootChksum)
         if len(inRootChecked) != 7:
            hasError = True
         elif inRootChecked != inRootData:
            nError += 1
      except:
         hasError = True

      # If the root ID is busted, stop.
      if hasError:
         (errType, errVal) = sys.exc_info()[:2]
         reply = QMessageBox.critical(self, self.tr('Invalid Data'), self.tr(
               'There is an error in the root ID you entered that could not '
               'be fixed automatically.  Please double-check that you entered the '
               'text exactly as it appears on the wallet-backup page.<br><br>'),
               QMessageBox.Ok)
         LOGERROR('Error in root ID restore field')
         LOGERROR('Error Type: %s', errType)
         LOGERROR('Error Value: %s', errVal)
         return

      # Save the version/key byte and the root ID. For now, ignore the version.
      inRootVer = inRootChecked[0]  # 1 byte
      inRootID = inRootChecked[1:7] # 6 bytes

      # Read in the root data (public key & chain code) and handle any errors.
      for i in range(nLine):
         hasError = False
         try:
            rawEntry = str(self.pkccList[i].text())
            rawBin, err = readSixteenEasyBytes(rawEntry.replace(' ', ''))
            if err == 'Error_2+':  # 2+ bytes are wrong, so we need to stop.
               hasError = True
            elif err == 'Fixed_1': # 1 byte is wrong, so we may be okay.
               nError += 1
         except:
            hasError = True

         # If the root ID is busted, stop.
         if hasError:
            lineNumber = i+1
            reply = QMessageBox.critical(self, self.tr('Invalid Data'), self.tr(
               'There is an error in the root data you entered that could not be '
               'fixed automatically.  Please double-check that you entered the '
               'text exactly as it appears on the wallet-backup page.  <br><br>'
               'The error occured on <font color="red">line #%1</font>.').arg(lineNumber), QMessageBox.Ok)
            LOGERROR('Error in root data restore field')
            return

         # If we've gotten this far, save the incoming line.
         inputLines.append(rawBin)

      # Set up the root ID data.
      pkVer = binary_to_int(inRootVer) & PYROOTPKCCVERMASK  # Ignored for now.
      pkSignByte = ((binary_to_int(inRootVer) & PYROOTPKCCSIGNMASK) >> 7) + 2
      rootPKComBin = int_to_binary(pkSignByte) + ''.join(inputLines[:2])
      rootPubKey = CryptoECDSA().UncompressPoint(SecureBinaryData(rootPKComBin))
      rootChainCode = SecureBinaryData(''.join(inputLines[2:]))

      # Now we should have a fully-plaintext root key and chain code, and can
      # get some related data.
      root = PyBtcAddress().createFromPublicKeyData(rootPubKey)
      root.chaincode = rootChainCode
      first = root.extendAddressChain()
      newWltID = binary_to_base58(inRootID)

      # Stop here if this was just a test
      if self.thisIsATest:
         verifyRecoveryTestID(self, newWltID, self.testWltID)
         return

      # If we already have the wallet, don't replace it, otherwise proceed.
      dlgOwnWlt = None
      if self.main.walletMap.has_key(newWltID):
         QMessageBox.warning(self, self.tr('Wallet Already Exists'), self.tr(
                             'The wallet already exists and will not be '
                             'replaced.'), QMessageBox.Ok)
         self.reject()
         return
      else:
         # Make sure the user is restoring the wallet they want to restore.
         reply = QMessageBox.question(self, self.tr('Verify Wallet ID'), \
                  self.tr('The data you entered corresponds to a wallet with a wallet '
                  'ID: \n\n\t%1\n\nDoes this '
                  'ID match the "Wallet Unique ID" you intend to restore? '
                  'If not, click "No" and enter the key and chain-code data '
                  'again.').arg(binary_to_base58(inRootID)), QMessageBox.Yes | QMessageBox.No)
         if reply == QMessageBox.No:
            return

         # Create the wallet.
         self.newWallet = PyBtcWallet().createNewWalletFromPKCC(rootPubKey, \
                                                                rootChainCode)

         # Create some more addresses and show a progress bar while restoring.
         nPool = 1000
         fillAddrPoolProgress = DlgProgress(self, self.main, HBar=1,
                                            Title=self.tr("Computing New Addresses"))
         fillAddrPoolProgress.exec_(self.newWallet.fillAddressPool, nPool)

      self.accept()


################################################################################
class DlgRestoreFragged(ArmoryDialog):
   def __init__(self, parent, main, thisIsATest=False, expectWltID=None):
      super(DlgRestoreFragged, self).__init__(parent, main)

      self.thisIsATest = thisIsATest
      self.testWltID = expectWltID
      headerStr = ''
      if thisIsATest:
         headerStr = self.tr('<font color="blue" size="4">Testing a '
                     'Fragmented Backup</font>')
      else:
         headerStr = self.tr('Restore Wallet from Fragments')

      descr = self.trUtf8(
         '<b><u>%1</u></b> <br><br>'
         'Use this form to enter all the fragments to be restored.  Fragments '
         'can be stored on a mix of paper printouts, and saved files. '
         u'If any of the fragments require a SecurePrint\u200b\u2122 code, '
         'you will only have to enter it once, since that code is the same for '
         'all fragments of any given wallet.').arg(headerStr)

      if self.thisIsATest:
         descr += self.tr('<br><br>'
            '<b>For testing purposes, you may enter more fragments than needed '
            'and Armory will test all subsets of the entered fragments to verify '
            'that each one still recovers the wallet successfully.</b>')

      lblDescr = QRichLabel(descr)

      frmDescr = makeHorizFrame([lblDescr], STYLE_RAISED)

      # HLINE

      self.scrollFragInput = QScrollArea()
      self.scrollFragInput.setWidgetResizable(True)
      self.scrollFragInput.setMinimumHeight(150)

      lblFragList = QRichLabel(self.tr('Input Fragments Below:'), doWrap=False, bold=True)
      self.btnAddFrag = QPushButton(self.tr('+Frag'))
      self.btnRmFrag = QPushButton(self.tr('-Frag'))
      self.btnRmFrag.setVisible(False)
      self.connect(self.btnAddFrag, SIGNAL(CLICKED), self.addFragment)
      self.connect(self.btnRmFrag, SIGNAL(CLICKED), self.removeFragment)
      self.chkEncrypt = QCheckBox(self.tr('Encrypt Restored Wallet'))
      self.chkEncrypt.setChecked(True)
      frmAddRm = makeHorizFrame([self.chkEncrypt, STRETCH, self.btnRmFrag, self.btnAddFrag])

      self.fragDataMap = {}
      self.tableSize = 2
      self.wltType = UNKNOWN
      self.fragIDPrefix = UNKNOWN

      doItText = self.tr('Test Backup') if thisIsATest else self.tr('Restore from Fragments')

      btnExit = QPushButton(self.tr('Cancel'))
      self.btnRestore = QPushButton(doItText)
      self.connect(btnExit, SIGNAL(CLICKED), self.reject)
      self.connect(self.btnRestore, SIGNAL(CLICKED), self.processFrags)
      frmBtns = makeHorizFrame([btnExit, STRETCH, self.btnRestore])

      self.lblRightFrm = QRichLabel('', hAlign=Qt.AlignHCenter)
      self.lblSecureStr = QRichLabel(self.trUtf8(u'SecurePrint\u200b\u2122 Code:'), \
                                     hAlign=Qt.AlignHCenter,
                                     doWrap=False,
                                     color='TextWarn')
      self.displaySecureString = QLineEdit()
      self.imgPie = QRichLabel('', hAlign=Qt.AlignHCenter)
      self.imgPie.setMinimumWidth(96)
      self.imgPie.setMinimumHeight(96)
      self.lblReqd = QRichLabel('', hAlign=Qt.AlignHCenter)
      self.lblWltID = QRichLabel('', doWrap=False, hAlign=Qt.AlignHCenter)
      self.lblFragID = QRichLabel('', doWrap=False, hAlign=Qt.AlignHCenter)
      self.lblSecureStr.setVisible(False)
      self.displaySecureString.setVisible(False)
      self.displaySecureString.setMaximumWidth(relaxedSizeNChar(self.displaySecureString, 16)[0])
      # The Secure String is now edited in DlgEnterOneFrag, It is only displayed here
      self.displaySecureString.setEnabled(False)
      frmSecPair = makeVertFrame([self.lblSecureStr, self.displaySecureString])
      frmSecCtr = makeHorizFrame([STRETCH, frmSecPair, STRETCH])

      frmWltInfo = makeVertFrame([STRETCH,
                                   self.lblRightFrm,
                                   self.imgPie,
                                   self.lblReqd,
                                   self.lblWltID,
                                   self.lblFragID,
                                   HLINE(),
                                   frmSecCtr,
                                   'Strut(200)',
                                   STRETCH], STYLE_SUNKEN)


      fragmentsLayout = QGridLayout()
      fragmentsLayout.addWidget(frmDescr, 0, 0, 1, 2)
      fragmentsLayout.addWidget(frmAddRm, 1, 0, 1, 1)
      fragmentsLayout.addWidget(self.scrollFragInput, 2, 0, 1, 1)
      fragmentsLayout.addWidget(frmWltInfo, 1, 1, 2, 1)
      setLayoutStretchCols(fragmentsLayout, 1, 0)

      walletRestoreTabs = QTabWidget()
      fragmentsFrame = QFrame()
      fragmentsFrame.setLayout(fragmentsLayout)
      walletRestoreTabs.addTab(fragmentsFrame, self.tr("Fragments"))
      self.advancedOptionsTab = AdvancedOptionsFrame(parent, main)
      walletRestoreTabs.addTab(self.advancedOptionsTab, self.tr("Advanced Options"))

      self.chkEncrypt.setChecked(not thisIsATest)
      self.chkEncrypt.setVisible(not thisIsATest)
      self.advancedOptionsTab.setEnabled(not thisIsATest)
      if not thisIsATest:
         self.connect(self.chkEncrypt, SIGNAL(CLICKED), self.onEncryptCheckboxChange)

      layout = QVBoxLayout()
      layout.addWidget(walletRestoreTabs)
      layout.addWidget(frmBtns)
      self.setLayout(layout)
      self.setMinimumWidth(650)
      self.setMinimumHeight(500)
      self.sizeHint = lambda: QSize(800, 650)
      self.setWindowTitle(self.tr('Restore wallet from fragments'))

      self.makeFragInputTable()
      self.checkRestoreParams()

   #############################################################################
   # Hide advanced options whenver the restored wallet is unencrypted
   def onEncryptCheckboxChange(self):
      self.advancedOptionsTab.setEnabled(self.chkEncrypt.isChecked())

   def makeFragInputTable(self, addCount=0):

      self.tableSize += addCount
      newLayout = QGridLayout()
      newFrame = QFrame()
      self.fragsDone = []
      newLayout.addWidget(HLINE(), 0, 0, 1, 5)
      for i in range(self.tableSize):
         btnEnter = QPushButton(self.tr('Type Data'))
         btnLoad = QPushButton(self.tr('Load File'))
         btnClear = QPushButton(self.tr('Clear'))
         lblFragID = QRichLabel('', doWrap=False)
         lblSecure = QLabel('')
         if i in self.fragDataMap:
            M, fnum, wltID, doMask, fid = ReadFragIDLineBin(self.fragDataMap[i][0])
            self.fragsDone.append(fnum)
            lblFragID.setText('<b>' + fid + '</b>')
            if doMask:
               lblFragID.setText('<b>' + fid + '</b>', color='TextWarn')


         self.connect(btnEnter, SIGNAL(CLICKED), \
                      functools.partial(self.dataEnter, fnum=i))
         self.connect(btnLoad, SIGNAL(CLICKED), \
                      functools.partial(self.dataLoad, fnum=i))
         self.connect(btnClear, SIGNAL(CLICKED), \
                      functools.partial(self.dataClear, fnum=i))


         newLayout.addWidget(btnEnter, 2 * i + 1, 0)
         newLayout.addWidget(btnLoad, 2 * i + 1, 1)
         newLayout.addWidget(btnClear, 2 * i + 1, 2)
         newLayout.addWidget(lblFragID, 2 * i + 1, 3)
         newLayout.addWidget(lblSecure, 2 * i + 1, 4)
         newLayout.addWidget(HLINE(), 2 * i + 2, 0, 1, 5)

      btnFrame = QFrame()
      btnFrame.setLayout(newLayout)

      frmFinal = makeVertFrame([btnFrame, STRETCH], STYLE_SUNKEN)
      self.scrollFragInput.setWidget(frmFinal)

      self.btnAddFrag.setVisible(self.tableSize < 12)
      self.btnRmFrag.setVisible(self.tableSize > 2)


   #############################################################################
   def addFragment(self):
      self.makeFragInputTable(1)

   #############################################################################
   def removeFragment(self):
      self.makeFragInputTable(-1)
      toRemove = []
      for key, val in self.fragDataMap.iteritems():
         if key >= self.tableSize:
            toRemove.append(key)

      # Have to do this in a separate loop, cause you can't remove items
      # from a map while you are iterating over them
      for key in toRemove:
         self.dataClear(key)


   #############################################################################
   def dataEnter(self, fnum):
      dlg = DlgEnterOneFrag(self, self.main, self.fragsDone, self.wltType, self.displaySecureString.text())
      if dlg.exec_():
         LOGINFO('Good data from enter_one_frag exec! %d', fnum)
         self.displaySecureString.setText(dlg.editSecurePrint.text())
         self.addFragToTable(fnum, dlg.fragData)
         self.makeFragInputTable()


   #############################################################################
   def dataLoad(self, fnum):
      LOGINFO('Loading data for entry, %d', fnum)
      toLoad = unicode(self.main.getFileLoad('Load Fragment File', \
                                    ['Wallet Fragments (*.frag)']))

      if len(toLoad) == 0:
         return

      if not os.path.exists(toLoad):
         LOGERROR('File just chosen does not exist! %s', toLoad)
         QMessageBox.critical(self, self.tr('File Does Not Exist'), self.tr(
            'The file you select somehow does not exist...? '
            '<br><br>%1<br><br> Try a different file').arg(toLoad), \
            QMessageBox.Ok)

      fragMap = {}
      with open(toLoad, 'r') as fin:
         allData = [line.strip() for line in fin.readlines()]
         fragMap = {}
         for line in allData:
            if line[:2].lower() in ['id', 'x1', 'x2', 'x3', 'x4', \
                                         'y1', 'y2', 'y3', 'y4', \
                                         'f1', 'f2', 'f3', 'f4']:
               fragMap[line[:2].lower()] = line[3:].strip().replace(' ', '')


      cList, nList = [], []
      if len(fragMap) == 9:
         cList, nList = ['x', 'y'], ['1', '2', '3', '4']
      elif len(fragMap) == 5:
         cList, nList = ['f'], ['1', '2', '3', '4']
      elif len(fragMap) == 3:
         cList, nList = ['f'], ['1', '2']
      else:
         LOGERROR('Unexpected number of lines in the frag file, %d', len(fragMap))
         return

      fragData = []
      fragData.append(hex_to_binary(fragMap['id']))
      for c in cList:
         for n in nList:
            mapKey = c + n
            rawBin, err = readSixteenEasyBytes(fragMap[c + n])
            if err == 'Error_2+':
               QMessageBox.critical(self, self.tr('Fragment Error'), self.tr(
                  'There was an unfixable error in the fragment file: '
                  '<br><br> File: %1 <br> Line: %2 <br>').arg(toLoad, mapKey), \
                  QMessageBox.Ok)
               return
            fragData.append(SecureBinaryData(rawBin))
            rawBin = None

      self.addFragToTable(fnum, fragData)
      self.makeFragInputTable()


   #############################################################################
   def dataClear(self, fnum):
      if not fnum in self.fragDataMap:
         return

      for i in range(1, 3):
         self.fragDataMap[fnum][i].destroy()
      del self.fragDataMap[fnum]
      self.makeFragInputTable()
      self.checkRestoreParams()


   #############################################################################
   def checkRestoreParams(self):
      showRightFrm = False
      self.btnRestore.setEnabled(False)
      self.lblRightFrm.setText(self.tr(
         '<b>Start entering fragments into the table to left...</b>'))
      for row, data in self.fragDataMap.iteritems():
         showRightFrm = True
         M, fnum, wltIDBin, doMask, idBase58 = ReadFragIDLineBin(data[0])
         self.lblRightFrm.setText(self.tr('<b><u>Wallet Being Restored:</u></b>'))
         self.imgPie.setPixmap(QPixmap(':/frag%df.png' % M).scaled(96,96))
         self.lblReqd.setText(self.tr('<b>Frags Needed:</b> %1').arg(M))
         self.lblWltID.setText(self.tr('<b>Wallet:</b> %1').arg(binary_to_base58(wltIDBin)))
         self.lblFragID.setText(self.tr('<b>Fragments:</b> %1').arg(idBase58.split('-')[0]))
         self.btnRestore.setEnabled(len(self.fragDataMap) >= M)
         break

      anyMask = False
      for row, data in self.fragDataMap.iteritems():
         M, fnum, wltIDBin, doMask, idBase58 = ReadFragIDLineBin(data[0])
         if doMask:
            anyMask = True
            break
      # If all of the rows with a Mask have been removed clear the securePrintCode
      if  not anyMask:
         self.displaySecureString.setText('')
      self.lblSecureStr.setVisible(anyMask)
      self.displaySecureString.setVisible(anyMask)

      if not showRightFrm:
         self.fragIDPrefix = UNKNOWN
         self.wltType = UNKNOWN

      self.imgPie.setVisible(showRightFrm)
      self.lblReqd.setVisible(showRightFrm)
      self.lblWltID.setVisible(showRightFrm)
      self.lblFragID.setVisible(showRightFrm)


   #############################################################################
   def addFragToTable(self, tableIndex, fragData):

      if len(fragData) == 9:
         currType = '0'
      elif len(fragData) == 5:
         currType = BACKUP_TYPE_135A
      elif len(fragData) == 3:
         currType = BACKUP_TYPE_135C
      else:
         LOGERROR('How\'d we get fragData of size: %d', len(fragData))
         return

      if self.wltType == UNKNOWN:
         self.wltType = currType
      elif not self.wltType == currType:
         QMessageBox.critical(self, self.tr('Mixed fragment types'), self.tr(
            'You entered a fragment for a different wallet type.  Please check '
            'that all fragments are for the same wallet, of the same version, '
            'and require the same number of fragments.'), QMessageBox.Ok)
         LOGERROR('Mixing frag types!  How did that happen?')
         return


      M, fnum, wltIDBin, doMask, idBase58 = ReadFragIDLineBin(fragData[0])
      # If we don't know the Secure String Yet we have to get it
      if doMask and len(str(self.displaySecureString.text()).strip()) == 0:
         dlg = DlgEnterSecurePrintCode(self, self.main)
         if dlg.exec_():
            self.displaySecureString.setText(dlg.editSecurePrint.text())
         else:
            return

      if self.fragIDPrefix == UNKNOWN:
         self.fragIDPrefix = idBase58.split('-')[0]
      elif not self.fragIDPrefix == idBase58.split('-')[0]:
         QMessageBox.critical(self, self.tr('Multiple Wallets'), self.tr(
            'The fragment you just entered is actually for a different wallet '
            'than the previous fragments you entered.  Please double-check that '
            'all the fragments you are entering belong to the same wallet and '
            'have the "number of needed fragments" (M-value, in M-of-N).'), \
            QMessageBox.Ok)
         LOGERROR('Mixing fragments of different wallets! %s', idBase58)
         return


      if not self.verifyNonDuplicateFrag(fnum):
         QMessageBox.critical(self, self.tr('Duplicate Fragment'), self.tr(
            'You just input fragment #%1, but that fragment has already been '
            'entered!').arg(fnum), QMessageBox.Ok)
         return



      if currType == '0':
         X = SecureBinaryData(''.join([fragData[i].toBinStr() for i in range(1, 5)]))
         Y = SecureBinaryData(''.join([fragData[i].toBinStr() for i in range(5, 9)]))
      elif currType == BACKUP_TYPE_135A:
         X = SecureBinaryData(int_to_binary(fnum + 1, widthBytes=64, endOut=BIGENDIAN))
         Y = SecureBinaryData(''.join([fragData[i].toBinStr() for i in range(1, 5)]))
      elif currType == BACKUP_TYPE_135C:
         X = SecureBinaryData(int_to_binary(fnum + 1, widthBytes=32, endOut=BIGENDIAN))
         Y = SecureBinaryData(''.join([fragData[i].toBinStr() for i in range(1, 3)]))

      self.fragDataMap[tableIndex] = [fragData[0][:], X.copy(), Y.copy()]

      X.destroy()
      Y.destroy()
      self.checkRestoreParams()

   #############################################################################
   def verifyNonDuplicateFrag(self, fnum):
      for row, data in self.fragDataMap.iteritems():
         rowFrag = ReadFragIDLineBin(data[0])[1]
         if fnum == rowFrag:
            return False

      return True



   #############################################################################
   def processFrags(self):
      if self.chkEncrypt.isChecked() and self.advancedOptionsTab.getKdfSec() == -1:
            QMessageBox.critical(self, self.tr('Invalid Target Compute Time'), \
               self.tr('You entered Target Compute Time incorrectly.\n\nEnter: <Number> (ms, s)'), QMessageBox.Ok)
            return
      if self.chkEncrypt.isChecked() and self.advancedOptionsTab.getKdfBytes() == -1:
            QMessageBox.critical(self, self.tr('Invalid Max Memory Usage'), \
               self.tr('You entered Max Memory Usage incorrectly.\n\nEnter: <Number> (kB, MB)'), QMessageBox.Ok)
            return
      SECPRINT = HardcodedKeyMaskParams()
      pwd, ekey = '', ''
      if self.displaySecureString.isVisible():
         pwd = str(self.displaySecureString.text()).strip()
         maskKey = SECPRINT['FUNC_KDF'](pwd)

      fragMtrx, M = [], -1
      for row, trip in self.fragDataMap.iteritems():
         M, fnum, wltID, doMask, fid = ReadFragIDLineBin(trip[0])
         X, Y = trip[1], trip[2]
         if doMask:
            LOGINFO('Row %d needs unmasking' % row)
            Y = SECPRINT['FUNC_UNMASK'](Y, ekey=maskKey)
         else:
            LOGINFO('Row %d is already unencrypted' % row)
         fragMtrx.append([X.toBinStr(), Y.toBinStr()])

      typeToBytes = {'0': 64, BACKUP_TYPE_135A: 64, BACKUP_TYPE_135C: 32}
      nBytes = typeToBytes[self.wltType]


      if self.thisIsATest and len(fragMtrx) > M:
         self.testFragSubsets(fragMtrx, M)
         return


      SECRET = ReconstructSecret(fragMtrx, M, nBytes)
      for i in range(len(fragMtrx)):
         fragMtrx[i] = []

      LOGINFO('Final length of frag mtrx: %d', len(fragMtrx))
      LOGINFO('Final length of secret:    %d', len(SECRET))

      priv, chain = '', ''
      if len(SECRET) == 64:
         priv = SecureBinaryData(SECRET[:32 ])
         chain = SecureBinaryData(SECRET[ 32:])
      elif len(SECRET) == 32:
         priv = SecureBinaryData(SECRET)
         chain = DeriveChaincodeFromRootKey(priv)


      # If we got here, the data is valid, let's create the wallet and accept the dlg
      # Now we should have a fully-plaintext rootkey and chaincode
      root = PyBtcAddress().createFromPlainKeyData(priv)
      root.chaincode = chain

      first = root.extendAddressChain()
      newWltID = binary_to_base58((ADDRBYTE + first.getAddr160()[:5])[::-1])

      # If this is a test, then bail
      if self.thisIsATest:
         verifyRecoveryTestID(self, newWltID, self.testWltID)
         return

      dlgOwnWlt = None
      if self.main.walletMap.has_key(newWltID):
         dlgOwnWlt = DlgReplaceWallet(newWltID, self.parent, self.main)

         if (dlgOwnWlt.exec_()):
            if dlgOwnWlt.output == 0:
               return
         else:
            self.reject()
            return

      reply = QMessageBox.question(self, self.tr('Verify Wallet ID'), self.tr(
         'The data you entered corresponds to a wallet with the '
         'ID:<blockquote><b>{%1}</b></blockquote>Does this ID '
         'match the "Wallet Unique ID" printed on your paper backup? '
         'If not, click "No" and reenter key and chain-code data '
         'again.').arg(newWltID), QMessageBox.Yes | QMessageBox.No)
      if reply == QMessageBox.No:
         return


      passwd = []
      if self.chkEncrypt.isChecked():
         dlgPasswd = DlgChangePassphrase(self, self.main)
         if dlgPasswd.exec_():
            passwd = SecureBinaryData(str(dlgPasswd.edtPasswd1.text()))
         else:
            QMessageBox.critical(self, self.tr('Cannot Encrypt'), self.tr(
               'You requested your restored wallet be encrypted, but no '
               'valid passphrase was supplied.  Aborting wallet '
               'recovery.'), QMessageBox.Ok)
            return

      shortl = ''
      longl  = ''
      nPool  = 1000

      if dlgOwnWlt is not None:
         if dlgOwnWlt.Meta is not None:
            shortl = ' - %s' % (dlgOwnWlt.Meta['shortLabel'])
            longl  = dlgOwnWlt.Meta['longLabel']
            nPool = max(nPool, dlgOwnWlt.Meta['naddress'])

      if passwd:
         self.newWallet = PyBtcWallet().createNewWallet(\
                                 plainRootKey=priv, \
                                 chaincode=chain, \
                                 shortLabel='Restored - ' + newWltID + shortl, \
                                 longLabel=longl, \
                                 withEncrypt=True, \
                                 securePassphrase=passwd, \
                                 kdfTargSec=self.advancedOptionsTab.getKdfSec(), \
                                 kdfMaxMem=self.advancedOptionsTab.getKdfBytes(),
                                 isActuallyNew=False, \
                                 doRegisterWithBDM=False)
      else:
         self.newWallet = PyBtcWallet().createNewWallet(\
                                 plainRootKey=priv, \
                                 chaincode=chain, \
                                 shortLabel='Restored - ' + newWltID +shortl, \
                                 longLabel=longl, \
                                 withEncrypt=False, \
                                 isActuallyNew=False, \
                                 doRegisterWithBDM=False)


      # Will pop up a little "please wait..." window while filling addr pool
      fillAddrPoolProgress = DlgProgress(self, self.parent, HBar=1,
                                         Title=self.tr("Computing New Addresses"))
      fillAddrPoolProgress.exec_(self.newWallet.fillAddressPool, nPool)

      if dlgOwnWlt is not None:
         if dlgOwnWlt.Meta is not None:
            from armoryengine.PyBtcWallet import WLT_UPDATE_ADD
            for n_cmt in range(0, dlgOwnWlt.Meta['ncomments']):
               entrylist = []
               entrylist = list(dlgOwnWlt.Meta[n_cmt])
               self.newWallet.walletFileSafeUpdate([[WLT_UPDATE_ADD, entrylist[2], entrylist[1], entrylist[0]]])

         self.newWallet = PyBtcWallet().readWalletFile(self.newWallet.walletPath)
      self.accept()

   #############################################################################
   def testFragSubsets(self, fragMtrx, M):
      # If the user entered multiple fragments
      fragMap = {}
      for x, y in fragMtrx:
         fragMap[binary_to_int(x, BIGENDIAN) - 1] = [x, y]
      typeToBytes = {'0': 64, BACKUP_TYPE_135A: 64, BACKUP_TYPE_135C: 32}

      isRandom, results = testReconstructSecrets(fragMap, M, 100)
      def privAndChainFromRow(secret):
         priv, chain = None, None
         if len(secret) == 64:
            priv = SecureBinaryData(secret[:32 ])
            chain = SecureBinaryData(secret[ 32:])
            return (priv, chain)
         elif len(secret) == 32:
            priv = SecureBinaryData(secret)
            chain = DeriveChaincodeFromRootKey(priv)
            return (priv, chain)
         else:
            LOGERROR('Root secret is %s bytes ?!' % len(secret))
            raise KeyDataError

      results = [(row[0], privAndChainFromRow(row[1])) for row in results]
      subsAndIDs = [(row[0], calcWalletIDFromRoot(*row[1])) for row in results]

      DlgShowTestResults(self, isRandom, subsAndIDs, \
                                 M, len(fragMtrx), self.testWltID).exec_()


##########################################################################
class DlgShowTestResults(ArmoryDialog):
   #######################################################################
   def __init__(self, parent, isRandom, subsAndIDs, M, nFrag, expectID):
      super(DlgShowTestResults, self).__init__(parent, parent.main)

      accumSet = set()
      for sub, ID in subsAndIDs:
         accumSet.add(ID)

      allEqual = (len(accumSet) == 1)
      allCorrect = True
      testID = expectID
      if not testID:
         testID = subsAndIDs[0][1]

      allCorrect = testID == subsAndIDs[0][1]

      descr = ''
      nSubs = len(subsAndIDs)
      fact = lambda x: math.factorial(x)
      total = fact(nFrag) / (fact(M) * fact(nFrag - M))
      if isRandom:
         descr = self.tr(
            'The total number of fragment subsets (%1) is too high '
            'to test and display.  Instead, %2 subsets were tested '
            'at random.  The results are below ').arg(total, nSubs)
      else:
         descr = self.tr(
            'For the fragments you entered, there are a total of '
            '%1 possible subsets that can restore your wallet. '
            'The test results for all subsets are shown below').arg(total)

      lblDescr = QRichLabel(descr)

      lblWltIDDescr = QRichLabel(self.tr(
         'The wallet ID is computed from the first '
         'address in your wallet based on the root key data (and the '
         '"chain code").  Therefore, a matching wallet ID proves that '
         'the wallet will produce identical addresses.'))


      frmResults = QFrame()
      layout = QGridLayout()
      row = 0
      for sub, ID in subsAndIDs:
         subStrs = [str(s) for s in sub]
         subText = ', '.join(subStrs[:-1])
         dispTxt = self.tr(
            'Fragments <b>%1</b> and <b>%2</b> produce a '
            'wallet with ID "<b>%3</b>"').arg(subText, subStrs[-1], ID)

         chk = lambda: QPixmap(':/checkmark32.png').scaled(20, 20)
         _X_ = lambda: QPixmap(':/red_X.png').scaled(16, 16)

         lblTxt = QRichLabel(dispTxt)
         lblTxt.setWordWrap(False)
         lblPix = QLabel('')
         lblPix.setPixmap(chk() if ID == testID else _X_())
         layout.addWidget(lblTxt, row, 0)
         layout.addWidget(lblPix, row, 1)
         row += 1



      scrollResults = QScrollArea()
      frmResults = QFrame()
      frmResults.setLayout(layout)
      scrollResults.setWidget(frmResults)

      btnOkay = QPushButton(self.tr('Ok'))
      buttonBox = QDialogButtonBox()
      buttonBox.addButton(btnOkay, QDialogButtonBox.AcceptRole)
      self.connect(btnOkay, SIGNAL(CLICKED), self.accept)

      mainLayout = QVBoxLayout()
      mainLayout.addWidget(lblDescr)
      mainLayout.addWidget(scrollResults)
      mainLayout.addWidget(lblWltIDDescr)
      mainLayout.addWidget(buttonBox)
      self.setLayout(mainLayout)

      self.setWindowTitle(self.tr('Fragment Test Results'))
      self.setMinimumWidth(500)

################################################################################
class DlgEnterSecurePrintCode(ArmoryDialog):

   def __init__(self, parent, main):
      super(DlgEnterSecurePrintCode, self).__init__(parent, main)

      lblSecurePrintCodeDescr = QRichLabel(self.trUtf8(
         u'This fragment file requires a SecurePrint\u200b\u2122 code. '
         'You will only have to enter this code once since it is the same '
         'on all fragments.'))
      lblSecurePrintCodeDescr.setMinimumWidth(440)
      self.lblSP = QRichLabel(self.trUtf8(u'SecurePrint\u200b\u2122 Code: '), doWrap=False)
      self.editSecurePrint = QLineEdit()
      spFrame = makeHorizFrame([self.lblSP, self.editSecurePrint, STRETCH])

      self.btnAccept = QPushButton(self.tr("Done"))
      self.btnCancel = QPushButton(self.tr("Cancel"))
      self.connect(self.btnAccept, SIGNAL(CLICKED), self.verifySecurePrintCode)
      self.connect(self.btnCancel, SIGNAL(CLICKED), self.reject)
      buttonBox = QDialogButtonBox()
      buttonBox.addButton(self.btnAccept, QDialogButtonBox.AcceptRole)
      buttonBox.addButton(self.btnCancel, QDialogButtonBox.RejectRole)

      layout = QVBoxLayout()
      layout.addWidget(lblSecurePrintCodeDescr)
      layout.addWidget(spFrame)
      layout.addWidget(buttonBox)
      self.setLayout(layout)
      self.setWindowTitle(self.tr('Enter Secure Print Code'))

   def verifySecurePrintCode(self):
      # Prepare the key mask parameters
      SECPRINT = HardcodedKeyMaskParams()
      securePrintCode = str(self.editSecurePrint.text()).strip()

      if not checkSecurePrintCode(self, SECPRINT, securePrintCode):
         return

      self.accept()

################################################################################
class DlgEnterOneFrag(ArmoryDialog):

   def __init__(self, parent, main, fragList=[], wltType=UNKNOWN, securePrintCode=None):
      super(DlgEnterOneFrag, self).__init__(parent, main)
      self.fragData = []
      BLUE = htmlColor('TextBlue')
      already = ''
      if len(fragList) > 0:
         strList = ['<font color="%s">%d</font>' % (BLUE, f) for f in fragList]
         replStr = '[' + ','.join(strList[:]) + ']'
         already = self.tr('You have entered fragments %1, so far.').arg(replStr)

      lblDescr = QRichLabel(self.trUtf8(
         '<b><u>Enter Another Fragment...</u></b> <br><br> %1 '
         'The fragments can be entered in any order, as long as you provide '
         'enough of them to restore the wallet.  If any fragments use a '
         u'SecurePrint\u200b\u2122 code, please enter it once on the '
         'previous window, and it will be applied to all fragments that '
         'require it.').arg(already))

      self.version0Button = QRadioButton(self.tr( BACKUP_TYPE_0_TEXT), self)
      self.version135aButton = QRadioButton(self.tr( BACKUP_TYPE_135a_TEXT), self)
      self.version135aSPButton = QRadioButton(self.trUtf8( BACKUP_TYPE_135a_SP_TEXT), self)
      self.version135cButton = QRadioButton(self.tr( BACKUP_TYPE_135c_TEXT), self)
      self.version135cSPButton = QRadioButton(self.trUtf8( BACKUP_TYPE_135c_SP_TEXT), self)
      self.backupTypeButtonGroup = QButtonGroup(self)
      self.backupTypeButtonGroup.addButton(self.version0Button)
      self.backupTypeButtonGroup.addButton(self.version135aButton)
      self.backupTypeButtonGroup.addButton(self.version135aSPButton)
      self.backupTypeButtonGroup.addButton(self.version135cButton)
      self.backupTypeButtonGroup.addButton(self.version135cSPButton)
      self.version135cButton.setChecked(True)
      self.connect(self.backupTypeButtonGroup, SIGNAL('buttonClicked(int)'), self.changeType)

      # This value will be locked after the first fragment is entered.
      if wltType == UNKNOWN:
         self.version135cButton.setChecked(True)
      elif wltType == '0':
         self.version0Button.setChecked(True)
         self.version135aButton.setEnabled(False)
         self.version135aSPButton.setEnabled(False)
         self.version135cButton.setEnabled(False)
         self.version135cSPButton.setEnabled(False)
      elif wltType == BACKUP_TYPE_135A:
            # Could be 1.35a with or without SecurePrintCode so remove the rest
         self.version0Button.setEnabled(False)
         self.version135cButton.setEnabled(False)
         self.version135cSPButton.setEnabled(False)
         if securePrintCode:
            self.version135aSPButton.setChecked(True)
         else:
            self.version135aButton.setChecked(True)
      elif wltType == BACKUP_TYPE_135C:
         # Could be 1.35c with or without SecurePrintCode so remove the rest
         self.version0Button.setEnabled(False)
         self.version135aButton.setEnabled(False)
         self.version135aSPButton.setEnabled(False)
         if securePrintCode:
            self.version135cSPButton.setChecked(True)
         else:
            self.version135cButton.setChecked(True)

      lblType = QRichLabel(self.tr('<b>Backup Type:</b>'), doWrap=False)

      layoutRadio = QVBoxLayout()
      layoutRadio.addWidget(self.version0Button)
      layoutRadio.addWidget(self.version135aButton)
      layoutRadio.addWidget(self.version135aSPButton)
      layoutRadio.addWidget(self.version135cButton)
      layoutRadio.addWidget(self.version135cSPButton)
      layoutRadio.setSpacing(0)

      radioButtonFrame = QFrame()
      radioButtonFrame.setLayout(layoutRadio)

      frmBackupType = makeVertFrame([lblType, radioButtonFrame])

      self.prfxList = ['x1:', 'x2:', 'x3:', 'x4:', \
                       'y1:', 'y2:', 'y3:', 'y4:', \
                       'F1:', 'F2:', 'F3:', 'F4:']
      self.prfxList = [QLabel(p) for p in self.prfxList]
      inpMask = '<AAAA\ AAAA\ AAAA\ AAAA\ \ AAAA\ AAAA\ AAAA\ AAAA\ \ AAAA!'
      self.edtList = [MaskedInputLineEdit(inpMask) for i in range(12)]

      inpMaskID = '<HHHH\ HHHH\ HHHH\ HHHH!'
      self.lblID = QRichLabel('ID:')
      self.edtID = MaskedInputLineEdit(inpMaskID)

      frmAllInputs = QFrame()
      frmAllInputs.setFrameStyle(STYLE_RAISED)
      layoutAllInp = QGridLayout()

      # Add Secure Print row - Use supplied securePrintCode and
      # disable text entry if it is not None
      self.lblSP = QRichLabel(self.trUtf8(u'SecurePrint\u200b\u2122 Code:'), doWrap=False)
      self.editSecurePrint = QLineEdit()
      self.editSecurePrint.setEnabled(not securePrintCode)
      if (securePrintCode):
         self.editSecurePrint.setText(securePrintCode)
      self.frmSP = makeHorizFrame([STRETCH, self.lblSP, self.editSecurePrint])
      layoutAllInp.addWidget(self.frmSP, 0, 0, 1, 2)

      layoutAllInp.addWidget(self.lblID, 1, 0, 1, 1)
      layoutAllInp.addWidget(self.edtID, 1, 1, 1, 1)
      for i in range(12):
         layoutAllInp.addWidget(self.prfxList[i], i + 2, 0, 1, 2)
         layoutAllInp.addWidget(self.edtList[i], i + 2, 1, 1, 2)
      frmAllInputs.setLayout(layoutAllInp)

      self.btnAccept = QPushButton(self.tr("Done"))
      self.btnCancel = QPushButton(self.tr("Cancel"))
      self.connect(self.btnAccept, SIGNAL(CLICKED), self.verifyUserInput)
      self.connect(self.btnCancel, SIGNAL(CLICKED), self.reject)
      buttonBox = QDialogButtonBox()
      buttonBox.addButton(self.btnAccept, QDialogButtonBox.AcceptRole)
      buttonBox.addButton(self.btnCancel, QDialogButtonBox.RejectRole)

      layout = QVBoxLayout()
      layout.addWidget(lblDescr)
      layout.addWidget(HLINE())
      layout.addWidget(frmBackupType)
      layout.addWidget(frmAllInputs)
      layout.addWidget(buttonBox)
      self.setLayout(layout)


      self.setWindowTitle(self.tr('Restore Single-Sheet Backup'))
      self.setMinimumWidth(500)
      self.layout().setSizeConstraint(QLayout.SetFixedSize)
      self.changeType(self.backupTypeButtonGroup.checkedId())


   #############################################################################
   def changeType(self, sel):
      #            |-- X --| |-- Y --| |-- F --|
      if sel == self.backupTypeButtonGroup.id(self.version0Button):
         visList = [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0]
      elif sel == self.backupTypeButtonGroup.id(self.version135aButton) or \
           sel == self.backupTypeButtonGroup.id(self.version135aSPButton):
         visList = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1]
      elif sel == self.backupTypeButtonGroup.id(self.version135cButton) or \
           sel == self.backupTypeButtonGroup.id(self.version135cSPButton):
         visList = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0]
      else:
         LOGERROR('What the heck backup type is selected?  %d', sel)
         return

      self.frmSP.setVisible(sel == self.backupTypeButtonGroup.id(self.version135aSPButton) or \
                            sel == self.backupTypeButtonGroup.id(self.version135cSPButton))
      for i in range(12):
         self.prfxList[i].setVisible(visList[i] == 1)
         self.edtList[ i].setVisible(visList[i] == 1)



   #############################################################################
   def destroyFragData(self):
      for line in self.fragData:
         if not isinstance(line, basestring):
            # It's an SBD Object.  Destroy it.
            line.destroy()

   #############################################################################
   def isSecurePrintID(self):
      return hex_to_int(str(self.edtID.text()[:2])) > 127

   #############################################################################
   def verifyUserInput(self):
      self.fragData = []
      nError = 0
      rawBin = None

      sel = self.backupTypeButtonGroup.checkedId()
      rng = [-1]
      if   sel == self.backupTypeButtonGroup.id(self.version0Button):
         rng = range(8)
      elif sel == self.backupTypeButtonGroup.id(self.version135aButton) or \
           sel == self.backupTypeButtonGroup.id(self.version135aSPButton):
         rng = range(8, 12)
      elif sel == self.backupTypeButtonGroup.id(self.version135cButton) or \
           sel == self.backupTypeButtonGroup.id(self.version135cSPButton):
         rng = range(8, 10)


      if sel == self.backupTypeButtonGroup.id(self.version135aSPButton) or \
         sel == self.backupTypeButtonGroup.id(self.version135cSPButton):
         # Prepare the key mask parameters
         SECPRINT = HardcodedKeyMaskParams()
         securePrintCode = str(self.editSecurePrint.text()).strip()
         if not checkSecurePrintCode(self, SECPRINT, securePrintCode):
            return
      elif self.isSecurePrintID():
            QMessageBox.critical(self, 'Bad Encryption Code', self.tr(
               'The ID field indicates that this is a SecurePrint '
               'Backup Type. You have either entered the ID incorrectly or '
               'have chosen an incorrect Backup Type.'), QMessageBox.Ok)
            return
      for i in rng:
         hasError = False
         try:
            rawEntry = str(self.edtList[i].text())
            rawBin, err = readSixteenEasyBytes(rawEntry.replace(' ', ''))
            if err == 'Error_2+':
               hasError = True
            elif err == 'Fixed_1':
               nError += 1
         except KeyError:
            hasError = True

         if hasError:
            reply = QMessageBox.critical(self, self.tr('Verify Wallet ID'), self.tr(
               'There is an error in the data you entered that could not be '
               'fixed automatically.  Please double-check that you entered the '
               'text exactly as it appears on the wallet-backup page. <br><br> '
               'The error occured on the "%1" line.').arg(str(self.prfxList[i].text())), QMessageBox.Ok)
            LOGERROR('Error in wallet restore field')
            self.prfxList[i].setText('<font color="red">' + str(self.prfxList[i].text()) + '</font>')
            self.destroyFragData()
            return

         self.fragData.append(SecureBinaryData(rawBin))
         rawBin = None


      idLine = str(self.edtID.text()).replace(' ', '')
      self.fragData.insert(0, hex_to_binary(idLine))

      M, fnum, wltID, doMask, fid = ReadFragIDLineBin(self.fragData[0])

      reply = QMessageBox.question(self, self.tr('Verify Fragment ID'), self.tr(
         'The data you entered is for fragment: '
         '<br><br> <font color="%1" size=3><b>%2</b></font>  <br><br> '
         'Does this ID match the "Fragment:" field displayed on your backup? '
         'If not, click "No" and re-enter the fragment data.').arg(htmlColor('TextBlue'), fid), QMessageBox.Yes | QMessageBox.No)

      if reply == QMessageBox.Yes:
         self.accept()

def checkSecurePrintCode(context, SECPRINT, securePrintCode):
   result = True
   try:
      if len(securePrintCode) < 9:
         QMessageBox.critical(context, context.tr('Invalid Code'), context.trUtf8(
            u'You didn\'t enter a full SecurePrint\u200b\u2122 code.  This '
            'code is needed to decrypt your backup file.'), QMessageBox.Ok)
         result = False
      elif not SECPRINT['FUNC_CHKPWD'](securePrintCode):
         QMessageBox.critical(context, context.trUtf8(u'Bad SecurePrint\u200b\u2122 Code'), context.trUtf8(
            u'The SecurePrint\u200b\u2122 code you entered has an error '
            'in it.  Note that the code is case-sensitive.  Please verify '
            'you entered it correctly and try again.'), QMessageBox.Ok)
         result = False
   except NonBase58CharacterError as e:
      QMessageBox.critical(context, context.trUtf8(u'Bad SecurePrint\u200b\u2122 Code'), context.trUtf8(
         u'The SecurePrint\u200b\u2122 code you entered has unrecognized characters '
         'in it.  %1 Only the following characters are allowed: %2').arg(e.message, BASE58CHARS), QMessageBox.Ok)
      result = False
   return result

################################################################################
def verifyRecoveryTestID(parent, computedWltID, expectedWltID=None):

   if expectedWltID == None:
      # Testing an arbitrary paper backup
      yesno = QMessageBox.question(parent, parent.tr('Recovery Test'), parent.tr(
         'From the data you entered, Armory calculated the following '
         'wallet ID: <font color="blue"><b>%1</b></font> '
         '<br><br>'
         'Does this match the wallet ID on the backup you are '
         'testing?').arg(computedWltID), QMessageBox.Yes | QMessageBox.No)

      if yesno == QMessageBox.No:
         QMessageBox.critical(parent, parent.tr('Bad Backup!'), parent.tr(
            'If this is your only backup and you are sure that you entered '
            'the data correctly, then it is <b>highly recommended you stop using '
            'this wallet!</b>  If this wallet currently holds any funds, '
            'you should move the funds to a wallet that <u>does</u> '
            'have a working backup. '
            '<br><br> <br><br>'
            'Wallet ID of the data you entered: %1 <br>').arg(computedWltID), \
            QMessageBox.Ok)
      elif yesno == QMessageBox.Yes:
         MsgBoxCustom(MSGBOX.Good, parent.tr('Backup is Good!'), parent.tr(
            '<b>Your backup works!</b> '
            '<br><br>'
            'The wallet ID is computed from a combination of the root '
            'private key, the "chaincode" and the first address derived '
            'from those two pieces of data.  A matching wallet ID '
            'guarantees it will produce the same chain of addresses as '
            'the original.'))
   else:  # an expected wallet ID was supplied
      if not computedWltID == expectedWltID:
         QMessageBox.critical(parent, parent.tr('Bad Backup!'), parent.tr(
            'If you are sure that you entered the backup information '
            'correctly, then it is <b>highly recommended you stop using '
            'this wallet!</b>  If this wallet currently holds any funds, '
            'you should move the funds to a wallet that <u>does</u> '
            'have a working backup.'
            '<br><br>'
            'Computed wallet ID: %1 <br>'
            'Expected wallet ID: %2 <br><br>'
            'Is it possible that you loaded a different backup than the '
            'one you just made?').arg(computedWltID, 'expectedWltID'), \
            QMessageBox.Ok)
      else:
         MsgBoxCustom(MSGBOX.Good, parent.tr('Backup is Good!'), parent.tr(
            'Your backup works! '
            '<br><br> '
            'The wallet ID computed from the data you entered matches '
            'the expected ID.  This confirms that the backup produces '
            'the same sequence of private keys as the original wallet! '
            '<br><br> '
            'Computed wallet ID: %1 <br> '
            'Expected wallet ID: %2 <br> '
            '<br>').arg(computedWltID, expectedWltID ))

################################################################################
class DlgReplaceWallet(ArmoryDialog):

   #############################################################################
   def __init__(self, WalletID, parent, main):
      super(DlgReplaceWallet, self).__init__(parent, main)

      lblDesc = QLabel(self.tr(
                       '<b>You already have this wallet loaded!</b><br>'
                       'You can choose to:<br>'
                       '- Cancel wallet restore operation<br>'
                       '- Set new password and fix any errors<br>'
                       '- Overwrite old wallet (delete comments & labels)<br>'))

      self.WalletID = WalletID
      self.main = main
      self.Meta = None
      self.output = 0

      self.wltPath = main.walletMap[WalletID].walletPath

      self.btnAbort = QPushButton(self.tr('Cancel'))
      self.btnReplace = QPushButton(self.tr('Overwrite'))
      self.btnSaveMeta = QPushButton(self.tr('Merge'))

      self.connect(self.btnAbort, SIGNAL('clicked()'), self.reject)
      self.connect(self.btnReplace, SIGNAL('clicked()'), self.Replace)
      self.connect(self.btnSaveMeta, SIGNAL('clicked()'), self.SaveMeta)

      layoutDlg = QGridLayout()

      layoutDlg.addWidget(lblDesc,          0, 0, 4, 4)
      layoutDlg.addWidget(self.btnAbort,    4, 0, 1, 1)
      layoutDlg.addWidget(self.btnSaveMeta, 4, 1, 1, 1)
      layoutDlg.addWidget(self.btnReplace,  4, 2, 1, 1)

      self.setLayout(layoutDlg)
      self.setWindowTitle('Wallet already exists')

   #########
   def Replace(self):
      self.main.removeWalletFromApplication(self.WalletID)

      datestr = RightNowStr('%Y-%m-%d-%H%M')
      homedir = os.path.dirname(self.wltPath)

      oldpath = os.path.join(homedir, self.WalletID, datestr)
      try:
         if not os.path.exists(oldpath):
            os.makedirs(oldpath)
      except:
         LOGEXCEPT('Cannot create new folder in dataDir! Missing credentials?')
         self.reject()
         return

      oldname = os.path.basename(self.wltPath)
      self.newname = os.path.join(oldpath, '%s_old.wallet' % (oldname[0:-7]))

      os.rename(self.wltPath, self.newname)

      backup = '%s_backup.wallet' % (self.wltPath[0:-7])
      if os.path.exists(backup):
         os.remove(backup)

      self.output =1
      self.accept()

   #########
   def SaveMeta(self):
      from armoryengine.PyBtcWalletRecovery import PyBtcWalletRecovery

      metaProgress = DlgProgress(self, self.main, Title=self.tr('Ripping Meta Data'))
      getMeta = PyBtcWalletRecovery()
      self.Meta = metaProgress.exec_(getMeta.ProcessWallet,
                                     WalletPath=self.wltPath,
                                     Mode=RECOVERMODE.Meta,
                                     Progress=metaProgress.UpdateText)
      self.Replace()


###############################################################################
class DlgWltRecoverWallet(ArmoryDialog):
   def __init__(self, parent=None, main=None):
      super(DlgWltRecoverWallet, self).__init__(parent, main)

      self.edtWalletPath = QLineEdit()
      self.edtWalletPath.setFont(GETFONT('Fixed', 9))
      edtW,edtH = tightSizeNChar(self.edtWalletPath, 50)
      self.edtWalletPath.setMinimumWidth(edtW)
      self.btnWalletPath = QPushButton(self.tr('Browse File System'))

      self.connect(self.btnWalletPath, SIGNAL('clicked()'), self.selectFile)

      lblDesc = QRichLabel(self.tr(
         '<b>Wallet Recovery Tool: '
         '</b><br>'
         'This tool will recover data from damaged or inconsistent '
         'wallets.  Specify a wallet file and Armory will analyze the '
         'wallet and fix any errors with it. '
         '<br><br>'
         '<font color="%1">If any problems are found with the specified '
         'wallet, Armory will provide explanation and instructions to '
         'transition to a new wallet.').arg(htmlColor('TextWarn')))
      lblDesc.setScaledContents(True)

      lblWalletPath = QRichLabel(self.tr('Wallet Path:'))

      self.selectedWltID = None

      def doWltSelect():
         dlg = DlgWalletSelect(self, self.main, self.tr('Select Wallet...'), '')
         if dlg.exec_():
            self.selectedWltID = dlg.selectedID
            wlt = self.parent.walletMap[dlg.selectedID]
            self.edtWalletPath.setText(wlt.walletPath)

      self.btnWltSelect = QPushButton(self.tr("Select Loaded Wallet"))
      self.connect(self.btnWltSelect, SIGNAL(CLICKED), doWltSelect)

      layoutMgmt = QGridLayout()
      wltSltQF = QFrame()
      wltSltQF.setFrameStyle(STYLE_SUNKEN)

      layoutWltSelect = QGridLayout()
      layoutWltSelect.addWidget(lblWalletPath,      0,0, 1, 1)
      layoutWltSelect.addWidget(self.edtWalletPath, 0,1, 1, 3)
      layoutWltSelect.addWidget(self.btnWltSelect,  1,0, 1, 2)
      layoutWltSelect.addWidget(self.btnWalletPath, 1,2, 1, 2)
      layoutWltSelect.setColumnStretch(0, 0)
      layoutWltSelect.setColumnStretch(1, 1)
      layoutWltSelect.setColumnStretch(2, 1)
      layoutWltSelect.setColumnStretch(3, 0)

      wltSltQF.setLayout(layoutWltSelect)

      layoutMgmt.addWidget(makeHorizFrame([lblDesc], STYLE_SUNKEN), 0,0, 2,4)
      layoutMgmt.addWidget(wltSltQF, 2, 0, 3, 4)

      self.rdbtnStripped = QRadioButton('', parent=self)
      self.connect(self.rdbtnStripped, SIGNAL('event()'), self.rdClicked)
      lblStripped = QLabel(self.tr('<b>Stripped Recovery</b><br>Only attempts to \
                            recover the wallet\'s rootkey and chaincode'))
      layout_StrippedH = QGridLayout()
      layout_StrippedH.addWidget(self.rdbtnStripped, 0, 0, 1, 1)
      layout_StrippedH.addWidget(lblStripped, 0, 1, 2, 19)

      self.rdbtnBare = QRadioButton('')
      lblBare = QLabel(self.tr('<b>Bare Recovery</b><br>Attempts to recover all private key related data'))
      layout_BareH = QGridLayout()
      layout_BareH.addWidget(self.rdbtnBare, 0, 0, 1, 1)
      layout_BareH.addWidget(lblBare, 0, 1, 2, 19)

      self.rdbtnFull = QRadioButton('')
      self.rdbtnFull.setChecked(True)
      lblFull = QLabel(self.tr('<b>Full Recovery</b><br>Attempts to recover as much data as possible'))
      layout_FullH = QGridLayout()
      layout_FullH.addWidget(self.rdbtnFull, 0, 0, 1, 1)
      layout_FullH.addWidget(lblFull, 0, 1, 2, 19)

      self.rdbtnCheck = QRadioButton('')
      lblCheck = QLabel(self.tr('<b>Consistency Check</b><br>Checks wallet consistency. Works with both full and watch only<br> wallets.'
                         ' Unlocking of encrypted wallets is not mandatory'))
      layout_CheckH = QGridLayout()
      layout_CheckH.addWidget(self.rdbtnCheck, 0, 0, 1, 1)
      layout_CheckH.addWidget(lblCheck, 0, 1, 3, 19)


      layoutMode = QGridLayout()
      layoutMode.addLayout(layout_StrippedH, 0, 0, 2, 4)
      layoutMode.addLayout(layout_BareH, 2, 0, 2, 4)
      layoutMode.addLayout(layout_FullH, 4, 0, 2, 4)
      layoutMode.addLayout(layout_CheckH, 6, 0, 3, 4)


      #self.rdnGroup = QButtonGroup()
      #self.rdnGroup.addButton(self.rdbtnStripped)
      #self.rdnGroup.addButton(self.rdbtnBare)
      #self.rdnGroup.addButton(self.rdbtnFull)
      #self.rdnGroup.addButton(self.rdbtnCheck)


      layoutMgmt.addLayout(layoutMode, 5, 0, 9, 4)
      """
      wltModeQF = QFrame()
      wltModeQF.setFrameStyle(STYLE_SUNKEN)
      wltModeQF.setLayout(layoutMode)

      layoutMgmt.addWidget(wltModeQF, 5, 0, 9, 4)
      wltModeQF.setVisible(False)


      btnShowAllOpts = QLabelButton(self.tr("All Recovery Options>>>"))
      frmBtn = makeHorizFrame(['Stretch', btnShowAllOpts, 'Stretch'], STYLE_SUNKEN)
      layoutMgmt.addWidget(frmBtn, 5, 0, 9, 4)

      def expandOpts():
         wltModeQF.setVisible(True)
         btnShowAllOpts.setVisible(False)
      self.connect(btnShowAllOpts, SIGNAL('clicked()'), expandOpts)

      if not self.main.usermode==USERMODE.Expert:
         frmBtn.setVisible(False)
      """

      self.btnRecover = QPushButton(self.tr('Recover'))
      self.btnCancel  = QPushButton(self.tr('Cancel'))
      layout_btnH = QHBoxLayout()
      layout_btnH.addWidget(self.btnRecover, 1)
      layout_btnH.addWidget(self.btnCancel, 1)

      def updateBtn(qstr):
         if os.path.exists(unicode(qstr).strip()):
            self.btnRecover.setEnabled(True)
            self.btnRecover.setToolTip('')
         else:
            self.btnRecover.setEnabled(False)
            self.btnRecover.setToolTip(self.tr('The entered path does not exist'))

      updateBtn('')
      self.connect(self.edtWalletPath, SIGNAL('textChanged(QString)'), updateBtn)


      layoutMgmt.addLayout(layout_btnH, 14, 1, 1, 2)

      self.connect(self.btnRecover, SIGNAL('clicked()'), self.accept)
      self.connect(self.btnCancel , SIGNAL('clicked()'), self.reject)

      self.setLayout(layoutMgmt)
      self.layout().setSizeConstraint(QLayout.SetFixedSize)
      self.setWindowTitle(self.tr('Wallet Recovery Tool'))
      self.setMinimumWidth(550)

   def rdClicked(self):
      # TODO:  Why does this do nohting?  Was it a stub that was forgotten?
      LOGINFO("clicked")

   def promptWalletRecovery(self):
      """
      Prompts the user with a window asking for wallet path and recovery mode.
      Proceeds to Recover the wallet. Prompt for password if the wallet is locked
      """
      if self.exec_():
         path = unicode(self.edtWalletPath.text())
         mode = RECOVERMODE.Bare
         if self.rdbtnStripped.isChecked():
            mode = RECOVERMODE.Stripped
         elif self.rdbtnFull.isChecked():
            mode = RECOVERMODE.Full
         elif self.rdbtnCheck.isChecked():
            mode = RECOVERMODE.Check

         if mode==RECOVERMODE.Full and self.selectedWltID:
            # Funnel all standard, full recovery operations through the
            # inconsistent-wallet-dialog.
            wlt = self.main.walletMap[self.selectedWltID]
            dlgRecoveryUI = DlgCorruptWallet(wlt, [], self.main, self, False)
            dlgRecoveryUI.exec_(dlgRecoveryUI.doFixWallets())
         else:
            # This is goatpig's original behavior - preserved for any
            # non-loaded wallets or non-full recovery operations.
            if self.selectedWltID:
               wlt = self.main.walletMap[self.selectedWltID]
            else:
               wlt = path

            dlgRecoveryUI = DlgCorruptWallet(wlt, [], self.main, self, False)
            dlgRecoveryUI.exec_(dlgRecoveryUI.ProcessWallet(mode))
      else:
         return False

   def selectFile(self):
      # Had to reimplement the path selection here, because the way this was
      # implemented doesn't let me access self.main.getFileLoad
      ftypes = self.tr('Wallet files (*.wallet);; All files (*)')
      if not OS_MACOSX:
         pathSelect = unicode(QFileDialog.getOpenFileName(self, \
                                 self.tr('Recover Wallet'), \
                                 ARMORY_HOME_DIR, \
                                 ftypes))
      else:
         pathSelect = unicode(QFileDialog.getOpenFileName(self, \
                                 self.tr('Recover Wallet'), \
                                 ARMORY_HOME_DIR, \
                                 ftypes, \
                                 options=QFileDialog.DontUseNativeDialog))

      self.edtWalletPath.setText(pathSelect)

# Need to put circular imports at the end of the script to avoid an import deadlock
from qtdialogs import CLICKED, STRETCH

