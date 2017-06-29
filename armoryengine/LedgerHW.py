from btchip.btchip import btchip
from btchip.btchipComm import HIDDongleHIDAPI
from btchip.btchipPersoWizard import StartBTChipPersoDialog
from btchip.btchipUtils import compress_public_key

from PyQt4.Qt import * #@UnusedWildImport
from PyQt4.QtGui import * #@UnusedWildImport
from qtdefines import * #@UnusedWildImport

import hid

from armoryengine.HardwareWallet import HardwareWallet, LEDGER_ENUM, BASE_KEYPATH, MASTER_XPUB_KEYPATH
from armoryengine.ArmoryUtils import *
from armoryengine.PyBtcWallet import buildWltFileName, WLT_UPDATE_ADD, WLT_DATATYPE_KEYDATA

# Choose the Ledger to setup
################################################################################
class DlgChooseLedger(ArmoryDialog):
   #############################################################################
   def __init__(self, parent, main):
      super(DlgChooseLedger, self).__init__(parent, main)

      lblDescr = QRichLabel(self.tr(
      '<b><u>Choose a Ledger Nano S to Setup</u></b> '
      '<br><br>'
      'Use this window to setup choose which Ledger Nano S hardware wallet '
      'to setup.'))


      lblType = QRichLabel(self.tr('<b>Available Devices:</b>'), doWrap=False)

      self.rdoBtnGrp = QButtonGroup()
      layoutRadio = QVBoxLayout()
      layoutRadio.setSpacing(0) 

      self.devices = []
      id = 0
      for hidDevice in hid.enumerate(0, 0):
         if hidDevice['vendor_id'] == 0x2c97: # Ledger Nano S
            print hidDevice
            dev = hid.device()
            dev.open_path(hidDevice['path'])
            dev.set_nonblocking(True)
            dongle = HIDDongleHIDAPI(dev, True, False)
            client = btchip(dongle)
            self.devices.append(client)
            rdo = QRadioButton(self.tr("Ledger Device [Serial Number: %1]")
               .arg(hidDevice['serial_number']))
            self.rdoBtnGrp.addButton(rdo)
            self.rdoBtnGrp.setId(rdo, id)
            id += 1
            rdo.setChecked(True)
            layoutRadio.addWidget(rdo)

      radioButtonFrame = QFrame()
      radioButtonFrame.setLayout(layoutRadio)

      self.btnAccept = QPushButton(self.tr('Next'))
      self.btnCancel = QPushButton(self.tr("Cancel"))
      self.connect(self.btnAccept, SIGNAL(CLICKED), self.nextDlg)
      self.connect(self.btnCancel, SIGNAL(CLICKED), self.reject)
      buttonBox = QDialogButtonBox()
      buttonBox.addButton(self.btnAccept, QDialogButtonBox.AcceptRole)
      buttonBox.addButton(self.btnCancel, QDialogButtonBox.RejectRole)

      layout = QVBoxLayout()
      layout.addWidget(radioButtonFrame)
      layout.addWidget(buttonBox)
      self.setLayout(layout)

      self.setWindowTitle(self.tr('Choose a Ledger to Setup'))

      self.setMinimumWidth(500)
      self.layout().setSizeConstraint(QLayout.SetFixedSize)

   def nextDlg(self):
      idx = self.rdoBtnGrp.checkedId()
      device = self.devices[idx]
      
      # Get master xpub from ledger
      result = device.getWalletPublicKey(MASTER_XPUB_KEYPATH)
      mpk = SecureBinaryData(str(result['publicKey']))
      chaincode = SecureBinaryData(str(result['chainCode']))
      print mpk.toHexStr()

      # Get first address public key
      result = device.getWalletPublicKey(BASE_KEYPATH + "0")
      firstAddrPub = SecureBinaryData(str(result['publicKey']))

      self.newWallet = LedgerWallet(device)
      self.newWallet.createNewWallet(masterPublicKey=mpk,
         mpkChaincode=chaincode, firstAddrPub=firstAddrPub)

      self.main.addWalletToApplication(self.newWallet)

      self.accept()

# Ledger wallet class
class LedgerWallet(HardwareWallet):
   def __init__(self, device):
      super(LedgerWallet, self).__init__()
      self.hardwareType = LEDGER_ENUM
      self.device = device

   #############################################################################
   def computeNextAddress(self, addr160=None, isActuallyNew=True, doRegister=True):
      """
      Use this to extend the chain beyond the last-computed address.

      We will usually be computing the next address from the tip of the 
      chain, but I suppose someone messing with the file format may
      leave gaps in the chain requiring some to be generated in the middle
      (then we can use the addr160 arg to specify which address to extend)
      """

      result = self.device.getWalletPublicKey("44'/0'/0'/0/" + str(self.lastComputedChainIndex + 1))
      newAddrPub = result['publicKey']

      newAddrSecPub = SecureBinaryData(str(newAddrPub))
      newAddr = PyBtcAddress().createFromPublicKeyData(newAddrSecPub)
      newAddr.chaincode = SecureBinaryData(str(result['chainCode']))
      newAddr.chainIndex = self.lastComputedChainIndex + 1

      new160 = newAddr.getAddr160()
      newDataLoc = self.walletFileSafeUpdate( \
         [[WLT_UPDATE_ADD, WLT_DATATYPE_KEYDATA, new160, newAddr]])
      self.addrMap[new160] = newAddr
      self.addrMap[new160].walletByteLoc = newDataLoc[0] + 21

      if newAddr.chainIndex > self.lastComputedChainIndex:
         self.lastComputedChainAddr160 = new160
         self.lastComputedChainIndex = newAddr.chainIndex

      self.linearAddr160List.append(new160)
      self.chainIndexMap[newAddr.chainIndex] = new160
      self.importList.append(len(self.linearAddr160List) - 1)
         
      if self.cppWallet != None:      
         needsRegistered = \
            self.cppWallet.extendAddressChainTo(self.lastComputedChainIndex)   
         
         if doRegister and self.isRegistered() and needsRegistered:
               self.cppWallet.registerWithBDV(isActuallyNew)

      return new160


# Need to put circular imports at the end of the script to avoid an import deadlock
from qtdialogs import CLICKED
from armoryengine.BDM import TheBDM, getCurrTimeAndBlock, BDM_BLOCKCHAIN_READY
from armoryengine.PyBtcAddress import PyBtcAddress