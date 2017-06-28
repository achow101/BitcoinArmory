from btchip.btchip import btchip
from btchip.btchipComm import HIDDongleHIDAPI
from btchip.btchipPersoWizard import StartBTChipPersoDialog
from btchip.btchipUtils import compress_public_key

from PyQt4.Qt import * #@UnusedWildImport
from PyQt4.QtGui import * #@UnusedWildImport
from qtdefines import * #@UnusedWildImport

import hid

from armoryengine.HardwareWallet import HardwareWallet, LEDGER_ENUM
from armoryengine.ArmoryUtils import *
from armoryengine.PyBtcWallet import buildWltFileName

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
      self.deviceIds = []
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
            self.deviceIds.append(hidDevice['serial_number'])
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
      deviceId = self.deviceIds[idx]
      
      # Get master xpub from ledger
      result = device.getWalletPublicKey("44'/0'/0'")
      mpk = compress_public_key(result['publicKey'])
      chaincode = result['chainCode']
      print result

      # Get first address public key
      result = device.getWalletPublicKey("44'/0'/0'/0")
      firstAddrPub = compress_public_key(result['publicKey'])
      print result

      self.newWallet = LedgerWallet().createNewWallet(masterPublicKey=mpk,
         mpkChaincode=chaincode, firstAddrPub=firstAddrPub, device=device, deviceId=deviceId)

      self.accept()

# Ledger wallet class
class LedgerWallet(HardwareWallet):
   def __init__(self):
      super(LedgerWallet, self).__init__()
      self.hardwareType = LEDGER_ENUM

   def createNewWallet(self, masterPublicKey, mpkChaincode, firstAddrPub, device, \
                        newWalletFilePath=None, deviceId='', \
                        shortLabel='', longLabel='', isActuallyNew=True, \
                        doRegisterWithBDM=True, skipBackupFile=False, \
                        Progress=emptyFunc, \
                        armoryHomeDir = ARMORY_HOME_DIR):
      """
      This method will create a new wallet, using as much customizability
      as you want.  You can enable encryption, and set the target params
      of the key-derivation function (compute-time and max memory usage).
      The KDF parameters will be experimentally determined to be as hard
      as possible for your computer within the specified time target
      (default, 0.25s).  It will aim for maximizing memory usage and using
      only 1 or 2 iterations of it, but this can be changed by scaling
      down the kdfMaxMem parameter (default 32 MB).

      If you use encryption, don't forget to supply a 32-byte passphrase,
      created via SecureBinaryData(pythonStr).  This method will apply
      the passphrase so that the wallet is "born" encrypted.

      We skip the atomic file operations since we don't even have
      a wallet file yet to safely update.

      DO NOT CALL THIS FROM BDM METHOD.  IT MAY DEADLOCK.
      """

      # Save hardware device info
      self.device = device
      self.deviceId = deviceId

      LOGINFO('***Creating new Ledger wallet')

      # Hardware wallets have no encryption, so no kdf or encryption params
      self.kdfKey = None
      
      # Create the root address object
      # Root address will be the address forthe  BIP 44 master public key
      mpkSecData = SecureBinaryData(str(masterPublicKey))
      rootAddr = PyBtcAddress()
      rootAddr.addrStr20 = mpkSecData.getHash160()
      rootAddr.binPublicKey65 = mpkSecData
      rootAddr.isInitialized = True
      rootAddr.isLocked = False
      rootAddr.useEncryption = False
      rootAddr.markAsRootAddr(SecureBinaryData(str(mpkChaincode)))

      firstAddrSecData = SecureBinaryData(str(firstAddrPub))
      firstAddr = PyBtcAddress()
      firstAddr.addrStr20 = mpkSecData.getHash160()
      firstAddr.binPublicKey65 = mpkSecData
      firstAddr.isInitialized = True
      firstAddr.isLocked = False
      firstAddr.useEncryption = False
      first160  = firstAddr.getAddr160()

      # Update wallet object with the new data
      # NEW IN WALLET VERSION 1.35:  unique ID is now based on
      # the first chained address: this guarantees that the unique ID
      # is based not only on the private key, BUT ALSO THE CHAIN CODE
      self.useEncryption = False
      self.addrMap['ROOT'] = rootAddr
      self.addrMap[firstAddr.getAddr160()] = firstAddr
      self.uniqueIDBin = (ADDRBYTE + firstAddr.getAddr160()[:5])[::-1]
      self.uniqueIDB58 = binary_to_base58(self.uniqueIDBin)
      self.labelName  = shortLabel[:32]   # aka "Wallet Name"
      self.labelDescr  = longLabel[:256]  # aka "Description"
      self.lastComputedChainAddr160 = first160
      self.lastComputedChainIndex  = firstAddr.chainIndex
      self.highestUsedChainIndex   = firstAddr.chainIndex - 1
      self.wltCreateDate = long(RightNow())
      self.linearAddr160List = [first160]
      self.chainIndexMap[firstAddr.chainIndex] = first160

      # We don't have to worry about atomic file operations when
      # creating the wallet: so we just do it naively here.
      self.walletPath = newWalletFilePath
      if not newWalletFilePath:
         shortName = self.labelName .replace(' ','_')
         # This was really only needed when we were putting name in filename
         #for c in ',?;:\'"?/\\=+-|[]{}<>':
            #shortName = shortName.replace(c,'_')
         newName = buildWltFileName(self.uniqueIDB58)
         self.walletPath = os.path.join(armoryHomeDir, newName)

      LOGINFO('   New wallet will be written to: %s', self.walletPath)
      newfile = open(self.walletPath, 'wb')
      fileData = BinaryPacker()

      # packHeader method writes KDF params and root address
      headerBytes = self.packHeader(fileData)

      # We make sure we have byte locations of the two addresses, to start
      self.addrMap[first160].walletByteLoc = headerBytes + 21

      fileData.put(BINARY_CHUNK, '\x00' + first160 + firstAddr.serialize())


      # Store the current localtime and blocknumber.  Block number is always 
      # accurate if available, but time may not be exactly right.  Whenever 
      # basing anything on time, please assume that it is up to one day off!
      time0,blk0 = getCurrTimeAndBlock() if isActuallyNew else (0,0)

      newfile.write(fileData.getBinaryString())
      newfile.close()

      if not skipBackupFile:
         walletFileBackup = self.getWalletPath('backup')
         shutil.copy(self.walletPath, walletFileBackup)

      # Let's fill the address pool while we are unlocked
      # It will get a lot more expensive if we do it on the next unlock
      self.fillAddressPool(self.addrPoolSize, isActuallyNew=isActuallyNew,
                              Progress=Progress, doRegister=doRegisterWithBDM)
         
      return self

   #############################################################################
   def computeNextAddress(self, addr160=None, isActuallyNew=True, doRegister=True):
      """
      Use this to extend the chain beyond the last-computed address.

      We will usually be computing the next address from the tip of the 
      chain, but I suppose someone messing with the file format may
      leave gaps in the chain requiring some to be generated in the middle
      (then we can use the addr160 arg to specify which address to extend)
      """

      result = self.device.getWalletPublicKey("44'/0'/0'/" + str(self.lastComputedChainIndex + 1))
      newAddrPub = compress_public_key(result['publicKey'])

      newAddrSecPub = SecureBinaryData(str(firstAddrPub))
      newAddr = PyBtcAddress()
      newAddr.addrStr20 = mpkSecData.getHash160()
      newAddr.binPublicKey65 = mpkSecData
      newAddr.isInitialized = True
      newAddr.isLocked = False
      newAddr.useEncryption = False
      newAddr.chainIndex = self.lastComputedChainIndex + 1
      newAddr.chaincode = SecureBinaryData(str(result['chainCode']))
      new160  = firstAddr.getAddr160()


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