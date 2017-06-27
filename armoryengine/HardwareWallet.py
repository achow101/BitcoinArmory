##############################################################################
#                                                                            #
# Copyright (C) 2017, goatpig                                             #
#  Distributed under the MIT license                                         #
#  See LICENSE-MIT or https://opensource.org/licenses/MIT                    #                                   
#                                                                            #
##############################################################################
import os.path
import shutil

from armoryengine.PyBtcWallet import PyBtcWallet, buildWltFileName, CheckWalletRegistration

#from CppBlockUtils import SecureBinaryData, KdfRomix, CryptoAES, CryptoECDSA
#import CppBlockUtils as Cpp
#from armoryengine.ArmoryUtils import *
#from armoryengine.BinaryPacker import *
#from armoryengine.BinaryUnpacker import *
#from armoryengine.Timer import *
#from armoryengine.Decorators import singleEntrantMethod
# This import is causing a circular import problem when used by findpass and promokit
# it is imported at the end of the file. Do not add it back at the begining
# from armoryengine.Transaction import *

# Version number for hardware wallets only 
HARDWARE_WALLET_VERSION  = (1, 40,  0, 0)  # (Major, Minor, Bugfix, AutoIncrement)

BLOCKCHAIN_READONLY   = 0
BLOCKCHAIN_READWRITE  = 1
BLOCKCHAIN_DONOTUSE   = 2

WLT_UPDATE_ADD = 0
WLT_UPDATE_MODIFY = 1

WLT_DATATYPE_KEYDATA     = 0
WLT_DATATYPE_ADDRCOMMENT = 1
WLT_DATATYPE_TXCOMMENT   = 2
WLT_DATATYPE_OPEVAL      = 3
WLT_DATATYPE_DELETED     = 4

DEFAULT_COMPUTE_TIME_TARGET = 0.25
DEFAULT_MAXMEM_LIMIT        = 32*1024*1024

PYROOTPKCCVER = 1 # Current version of root pub key/chain code backup format
PYROOTPKCCVERMASK = 0x7F
PYROOTPKCCSIGNMASK = 0x80

NO_HARDWARE_ENUM = 0
TREZOR_ENUM = 1
LEDGER_ENUM = 2
KEEPKEY_ENUM = 3
DIGITAL_BITBOX_ENUM = 4
   
class HardwareWallet(PyBtcWallet):
   """
   This class is a wrapper for PyBtcWallet to work with hardware wallets.
   This will be replaced with the python proxy for cppwallets later.

   For now, uses some of the unused space in PyBtcWallet:
   ---
   Hardware   -- (1) Enum for hardware type as defined in the constants of this file
   Device ID  -- (256) String with the device ID or serial number
   UNUSED     -- (767) unused space for future expansion of wallet file
   ---
   """
  #############################################################################
   def __init__(self):
      super().__init__()
      self.version        = HARDWARE_WALLET_VERSION  # (Major, Minor, Minor++, even-more-minor)
      self.watchingOnly   = True # Hardware wallets are always watching only
      self.useEncryption  = False # Watching only wallets are never enecrypted

      self.deviceId = ""
      self.hardwareType = NO_HARDWARE_ENUM

   #############################################################################
   def createNewWallet(self, masterPublicKey, firstAddrPub, newWalletFilePath=None, \
                             IV=None, kdfTargSec=DEFAULT_COMPUTE_TIME_TARGET, \
                             kdfMaxMem=DEFAULT_MAXMEM_LIMIT, \
                             shortLabel='', longLabel='', isActuallyNew=True, \
                             doRegisterWithBDM=True, skipBackupFile=False, \
                             extraEntropy=None, Progress=emptyFunc, \
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

      The field plainRootKey could be used to recover a written backup
      of a wallet, since all addresses are deterministically computed
      from the root address.  This obviously won't reocver any imported
      keys, but does mean that you can recover your ENTIRE WALLET from
      only those 32 plaintext bytes AND the 32-byte chaincode.

      We skip the atomic file operations since we don't even have
      a wallet file yet to safely update.

      DO NOT CALL THIS FROM BDM METHOD.  IT MAY DEADLOCK.
      """

      LOGINFO('***Creating new Hardware wallet')

      # Hardware wallets have no encryption, so no kdf or encryption params
      self.kdfKey = None
      
      # Zero out rootkey and chaincode
      plainRootKey = SecureBinaryData('\x00'*32)
      chaincode = SecureBinaryData('\xff'*32)

      # Create the root address object
      # Root address will be the address forthe  BIP 44 master public key
      rootAddr = PyBtcAddress().createFromPublicKeyData(masterPublicKey)
      rootAddr.markAsRootAddr(chaincode)

      firstAddr = PyBtcAddress().createFromPublicKeyData(firstAddrPub)
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
      self.lastComputedChainIndex  = first160.chainIndex
      self.highestUsedChainIndex   = first160.chainIndex - 1
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
   def advanceHighestIndex(self, ct=1, isNew=False):
      topIndex = self.highestUsedChainIndex + ct
      topIndex = min(topIndex, self.lastComputedChainIndex)
      topIndex = max(topIndex, 0)

      self.highestUsedChainIndex = topIndex
      self.walletFileSafeUpdate( [[WLT_UPDATE_MODIFY, self.offsetTopUsed, \
                    int_to_binary(self.highestUsedChainIndex, widthBytes=8)]])
      self.fillAddressPool(isActuallyNew=isNew)
         
   #############################################################################
   def peekNextUnusedAddr(self):
      return self.addrMap[self.getAddress160ByChainIndex(self.highestUsedChainIndex+1)]
   
   #############################################################################
   def getNextUnusedAddress(self):
      if self.lastComputedChainIndex - self.highestUsedChainIndex < \
                                              max(self.addrPoolSize,1):
         self.fillAddressPool(self.addrPoolSize, True)

      self.advanceHighestIndex(1, True)
      new160 = self.getAddress160ByChainIndex(self.highestUsedChainIndex)
      self.addrMap[new160].touch()
      self.walletFileSafeUpdate( [[WLT_UPDATE_MODIFY, \
                                  self.addrMap[new160].walletByteLoc, \
                                  self.addrMap[new160].serialize()]]  )
      return self.addrMap[new160]

   #############################################################################
   def fillAddressPool(self, numPool=None, isActuallyNew=True, 
                       doRegister=True, Progress=emptyFunc):
      """
      Usually, when we fill the address pool, we are generating addresses
      for the first time, and thus there is no chance it's ever seen the
      blockchain.  However, this method is also used for recovery/import 
      of wallets, where the address pool has addresses that probably have
      transactions already in the blockchain.  

      Filling the address pool is hardware specific so this is just a dummy
      that should be overriden later.
      """
      raise NotImplementedError("This method should be implemented by the child "
         "classes not the base class.")

   #############################################################################
   def getRootPKCC(self, pkIsCompressed=False):
      '''Hardware wallets should not implement this'''
      raise NotImplementedError('Hardware wallets should not implement this method')

   #############################################################################
   def packHeader(self, binPacker):
      if not self.addrMap['ROOT']:
         raise WalletAddressError('Cannot serialize uninitialzed wallet!')

      startByte = binPacker.getSize()

      binPacker.put(BINARY_CHUNK, self.fileTypeStr, width=8)
      binPacker.put(UINT32, getVersionInt(self.version))
      binPacker.put(BINARY_CHUNK, self.magicBytes,  width=4)

      # Wallet info flags
      self.offsetWltFlags = binPacker.getSize() - startByte
      self.packWalletFlags(binPacker)

      # Binary Unique ID (firstAddr25bytes[:5][::-1])
      binPacker.put(BINARY_CHUNK, self.uniqueIDBin, width=6)

      # Unix time of wallet creations
      binPacker.put(UINT64, self.wltCreateDate)

      # User-supplied wallet label (short)
      self.offsetLabelName = binPacker.getSize() - startByte
      binPacker.put(BINARY_CHUNK, self.labelName , width=32)

      # User-supplied wallet label (long)
      self.offsetLabelDescr = binPacker.getSize() - startByte
      binPacker.put(BINARY_CHUNK, self.labelDescr,  width=256)

      # Highest used address: 
      self.offsetTopUsed = binPacker.getSize() - startByte
      binPacker.put(INT64, self.highestUsedChainIndex)

      # Key-derivation function parameters
      self.offsetKdfParams = binPacker.getSize() - startByte
      binPacker.put(BINARY_CHUNK, self.serializeKdfParams(), width=256)

      # Wallet encryption parameters (currently nothing to put here)
      self.offsetCrypto = binPacker.getSize() - startByte
      binPacker.put(BINARY_CHUNK, self.serializeCryptoParams(), width=256)

      # Address-chain root, (base-address for deterministic wallets)
      self.offsetRootAddr = binPacker.getSize() - startByte
      self.addrMap['ROOT'].walletByteLoc = self.offsetRootAddr
      binPacker.put(BINARY_CHUNK, self.addrMap['ROOT'].serialize())

      # Hardware type
      self.offsetHardwareType = binPacker.getSize() - startByte
      binPacker.put(UINT8, self.hardwareType)

      # Device ID string
      self.offsetDeviceId = binPacker.getSize() - startByte
      binPacker.put(BINARY_CHUNK, self.deviceId, width=256)

      # In wallet version 1.40, this next 767 bytes is unused -- may be used in future
      binPacker.put(BINARY_CHUNK, '\x00'*767)
      return binPacker.getSize() - startByte

   #############################################################################
   def unpackHeader(self, binUnpacker):
      """
      Unpacking the header information from a wallet file.  See the help text
      on the base class, PyBtcWallet, for more information on the wallet
      serialization.
      """
      self.fileTypeStr = binUnpacker.get(BINARY_CHUNK, 8)
      self.version     = readVersionInt(binUnpacker.get(UINT32))
      self.magicBytes  = binUnpacker.get(BINARY_CHUNK, 4)

      # Decode the bits to get the flags
      self.offsetWltFlags = binUnpacker.getPosition()
      self.unpackWalletFlags(binUnpacker)

      # This is the first 4 bytes of the 25-byte address-chain-root address
      # This includes the network byte (i.e. main network, testnet, namecoin)
      self.uniqueIDBin = binUnpacker.get(BINARY_CHUNK, 6)
      self.uniqueIDB58 = binary_to_base58(self.uniqueIDBin)
      self.wltCreateDate  = binUnpacker.get(UINT64)

      # We now have both the magic bytes and network byte
      if not self.magicBytes == MAGIC_BYTES:
         LOGERROR('Requested wallet is for a different blockchain!')
         LOGERROR('Wallet is for:  %s ', BLOCKCHAINS[self.magicBytes])
         LOGERROR('ArmoryEngine:   %s ', BLOCKCHAINS[MAGIC_BYTES])
         return -1
      if not self.uniqueIDBin[-1] == ADDRBYTE:
         LOGERROR('Requested wallet is for a different network!')
         LOGERROR('ArmoryEngine:   %s ', NETWORKS[ADDRBYTE])
         return -2

      # User-supplied description/name for wallet
      self.offsetLabelName = binUnpacker.getPosition()
      self.labelName  = binUnpacker.get(BINARY_CHUNK, 32).strip('\x00')


      # Longer user-supplied description/name for wallet
      self.offsetLabelDescr  = binUnpacker.getPosition()
      self.labelDescr  = binUnpacker.get(BINARY_CHUNK, 256).strip('\x00')


      self.offsetTopUsed = binUnpacker.getPosition()
      self.highestUsedChainIndex = binUnpacker.get(INT64)


      # Read the key-derivation function parameters
      self.offsetKdfParams = binUnpacker.getPosition()
      self.kdf = self.unserializeKdfParams(binUnpacker)

      # Read the crypto parameters
      self.offsetCrypto    = binUnpacker.getPosition()
      self.crypto = self.unserializeCryptoParams(binUnpacker)

      # Read address-chain root address data
      self.offsetRootAddr  = binUnpacker.getPosition()      

      rawAddrData = binUnpacker.get(BINARY_CHUNK, self.pybtcaddrSize)
      self.addrMap['ROOT'] = PyBtcAddress().unserialize(rawAddrData)
      fixedAddrData = self.addrMap['ROOT'].serialize()
      if not rawAddrData==fixedAddrData:
         self.walletFileSafeUpdate([ \
            [WLT_UPDATE_MODIFY, self.offsetRootAddr, fixedAddrData]])

      self.addrMap['ROOT'].walletByteLoc = self.offsetRootAddr
      if self.useEncryption:
         self.addrMap['ROOT'].isLocked = True
         self.isLocked = True

      # Hardware type
      self.offsetHardwareType = binUnpacker.getPosition()
      self.hardwareType = binUnpacker.get(UINT8)

      # Device ID string
      self.offsetDeviceId = binUnpacker.getPosition()
      self.deviceId = binUnpacker.get(BINARY_CHUNK, 256).strip('\x00')

      # In wallet version 1.40, the next 767 bytes is unused -- may be used in future
      binUnpacker.advance(767)

      # TODO: automatic conversion if the code uses a newer wallet
      #       version than the wallet... got a manual script, but it
      #       would be nice to autodetect and correct
      #convertVersion

      return 0 #success

   #############################################################################
   def unpackNextEntry(self, binUnpacker):
      dtype   = binUnpacker.get(UINT8)
      hashVal = ''
      binData = ''
      if dtype==WLT_DATATYPE_KEYDATA:
         hashVal = binUnpacker.get(BINARY_CHUNK, 20)
         binData = binUnpacker.get(BINARY_CHUNK, self.pybtcaddrSize)
      elif dtype==WLT_DATATYPE_ADDRCOMMENT:
         hashVal = binUnpacker.get(BINARY_CHUNK, 20)
         commentLen = binUnpacker.get(UINT16)
         binData = binUnpacker.get(BINARY_CHUNK, commentLen)
      elif dtype==WLT_DATATYPE_TXCOMMENT:
         hashVal = binUnpacker.get(BINARY_CHUNK, 32)
         commentLen = binUnpacker.get(UINT16)
         binData = binUnpacker.get(BINARY_CHUNK, commentLen)
      elif dtype==WLT_DATATYPE_OPEVAL:
         raise NotImplementedError('OP_EVAL not support in wallet yet')
      elif dtype==WLT_DATATYPE_DELETED:
         deletedLen = binUnpacker.get(UINT16)
         binUnpacker.advance(deletedLen)
         

      return (dtype, hashVal, binData)


   #############################################################################
   def deleteImportedAddress(self, addr160):
      """
      Never delete imported addresses from a hardware wallet as all addresses are
      imported (for the hack)
      """
      raise NotImplementedError("This method should never be called on a hardware "
         "wallet as all addreses are imported.")

   #############################################################################
   def importExternalAddressData(self, pubKey=None,  pubChk=None, \
                                       addr20=None,  addrChk=None, \
                                       firstTime=UINT32_MAX, \
                                       firstBlk=UINT32_MAX, lastTime=0, \
                                       lastBlk=0, chainIndex = -2):
      """
      This wallet fully supports importing external keys, even though it is
      a deterministic wallet: determinism only adds keys to the pool based
      on the address-chain, but there's nothing wrong with adding new keys
      not on the chain.

      We don't know when this address was created, so we have to set its
      first/last-seen times to 0, to make sure we search the whole blockchain
      for tx related to it.  This data will be updated later after we've done
      the search and know for sure when it is "relevant".
      (alternatively, if you know it's first-seen time for some reason, you
      can supply it as an input, but this seems rare: we don't want to get it
      wrong or we could end up missing wallet-relevant transactions)

      DO NOT CALL FROM A BDM THREAD FUNCTION.  IT MAY DEADLOCK.
      """
      computedPubKey = None
      computedAddr20 = None

      # If public key is provided, we prep it so we can verify Pub/Priv match
      if pubKey:
         if isinstance(pubKey, str):
            pubKey = SecureBinaryData(pubKey)
         if pubChk:
            pubKey = SecureBinaryData(verifyChecksum(pubKey.toBinStr(), pubChk))

         if not computedAddr20:
            computedAddr20 = convertKeyDataToAddress(pubKey=pubKey)

      # The 20-byte address (pubkey hash160) should always be a python string
      if addr20:
         if not isinstance(pubKey, str):
            addr20 = addr20.toBinStr()
         if addrChk:
            addr20 = verifyChecksum(addr20, addrChk)

      # Now a few sanity checks
      if self.addrMap.has_key(addr20):
         LOGWARN('The address is already in your wallet!')
         return None

      addr20 = computedAddr20

      if self.addrMap.has_key(addr20):
         LOGERROR('The computed address is already in your wallet!')
         return None

      if pubKey:
         securePubKey = SecureBinaryData(pubKey)
         newAddr = PyBtcAddress().createFromPublicKeyData(securePubKey)
      else:
         newAddr = PyBtcAddress().createFromPublicKeyHash160(addr20)

      newAddr.chaincode  = SecureBinaryData('\xff'*32)
      newAddr.chainIndex = chainIndex
      newAddr.timeRange = [firstTime, lastTime]
      newAddr.blkRange  = [firstBlk,  lastBlk ]
      #newAddr.binInitVect16  = SecureBinaryData().GenerateRandom(16)
      newAddr160 = newAddr.getAddr160()

      newDataLoc = self.walletFileSafeUpdate( \
         [[WLT_UPDATE_ADD, WLT_DATATYPE_KEYDATA, newAddr160, newAddr]])
      self.addrMap[newAddr160] = newAddr.copy()
      self.addrMap[newAddr160].walletByteLoc = newDataLoc[0] + 21
      
      self.linearAddr160List.append(newAddr160)
      
   #############################################################################
   def signUnsignedTx(self, ustx, hashcode=1):
      # Do nothing here as this is hardware wallet specifi
      raise NotImplementedError('Signing transactions is not available for a '
         'generic hardware wallet. This is hardware wallet specific.')
      
      return ustx

   #############################################################################
   def getAddress160ByChainIndex(self, desiredIdx):
      """
      It should be safe to assume that if the index is less than the highest 
      computed, it will be in the chainIndexMap, but I don't like making such
      assumptions.  Perhaps something went wrong with the wallet, or it was
      manually reconstructed and has holes in the chain.  We will regenerate
      addresses up to that point, if necessary (but nothing past the value
      self.lastComputedChainIndex.
      """
      if desiredIdx>self.lastComputedChainIndex or desiredIdx<0:
         # I removed the option for fillPoolIfNecessary, because of the risk
         # that a bug may lead to generation of billions of addresses, which
         # would saturate the system's resources and fill the HDD.
         raise WalletAddressError('Chain index is out of range')

      if self.chainIndexMap.has_key(desiredIdx):
         return self.chainIndexMap[desiredIdx]
      else:
         # Somehow the address isn't here, even though it is less than the
         # last computed index
         # But too bad. This is a hardware wallet hack and we can't compute 
         # anymore addresses. Throw an exception
         raise WalletAddressError('Address for chain index does not exist')
         

# Putting this at the end because of the circular dependency
from armoryengine.BDM import TheBDM, getCurrTimeAndBlock, BDM_BLOCKCHAIN_READY
from armoryengine.PyBtcAddress import PyBtcAddress
from armoryengine.Transaction import *
from armoryengine.Script import scriptPushData

# kate: indent-width 3; replace-tabs on;