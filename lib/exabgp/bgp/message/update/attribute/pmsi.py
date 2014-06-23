# encoding: utf-8
"""
pmsi_tunnel.py

Created by Orange.
Copyright (c) 2014-2014, Orange. All rights reserved.
"""

import socket
from struct import pack,unpack

from exabgp.bgp.message.update.attribute import Attribute
from exabgp.bgp.message.update.attribute.id import AttributeID
from exabgp.bgp.message.update.attribute import Flag


# http://tools.ietf.org/html/rfc6514#section-5
#
#  +---------------------------------+
#  |  Flags (1 octet)                |
#  +---------------------------------+
#  |  Tunnel Type (1 octets)         |
#  +---------------------------------+
#  |  MPLS Label (3 octets)          |
#  +---------------------------------+
#  |  Tunnel Identifier (variable)   |
#  +---------------------------------+


# ========================================================================= PMSI
# RFC 6514

class PMSI (Attribute):
	ID = AttributeID.PMSI_TUNNEL
	FLAG = Flag.OPTIONAL
	MULTIPLE = False

	# TUNNEL_TYPE MUST NOT BE DEFINED HERE ( it allows to set it up as a self. value)

	_known = dict()
	_name = {
		0 : 'No tunnel',
		1 : 'RSVP-TE P2MP LSP',
		2 : 'mLDP P2MP LSP',
		3 : 'PIM-SSM Tree',
		4 : 'PIM-SM Tree',
		5 : 'BIDIR-PIM Tree',
		6 : 'Ingress Replication',
		7 : 'mLDP MP2MP LSP',
	}

	@classmethod
	def register (klass):
		klass._known[klass.TUNNEL_TYPE] = klass

	def __init__ (self,tunnel,label,flags):
		self.label = label    # integer
		self.flags = flags    # integer
		self.tunnel = tunnel  # tunnel id, packed data

	@staticmethod
	def name (tunnel_type):
		return PMSI._name.get(tunnel_type,'unknown')

	def pack(self):
		return self._attribute(
			pack('!BB3s',
				self.flags,
				self.TUNNEL_TYPE,
				pack('!L',self.label << 4)[1:4]
			)+ self.tunnel
		)

	# XXX: FIXME: Orange code had 4 (and another reference to it in the code elsewhere)
	def __len__ (self):
		return len(self.self.tunnel) + 5  # label:1, tunnel type: 1, MPLS label:3

	def __cmp__(self,other):
		if not isinstance(other,self.__class__):
			return -1
		# if self.TUNNEL_TYPE != other.TUNNEL_TYPE:
		# 	return -1
		if self.label != other.label:
			return -1
		if self.flags != other.flags:
			return -1
		if self.tunnel != other.tunnel:
			return -1
		return 0

	def __repr__ (self):
		return str(self)

	def prettytunnel (self):
		return "0x" + ''.join('%02X' % ord(_) for _ in self.tunnel) if self.tunnel else ''

	def __str__ (self):
		#TODO: add hex dump of packedValue
		return "pmsi:%s:%s:%s:%s" % (
			self.name(self.TUNNEL_TYPE).replace(' ','').lower(),
			str(self.flags) if self.flags else '-',  # why not use zero (0) ?
			str(self.label) if self.label else '-',  # what noy use zero (0) ?
			self.prettytunnel()
		)

	@staticmethod
	def unknown (subtype,tunnel,label,flags):
		pmsi = PMSI(tunnel,label,flags)
		pmsi.TUNNEL_TYPE = subtype
		return pmsi

	@staticmethod
	def unpack (data):
		flags,subtype = unpack('!BB',data[:2])
		label = unpack('!L','\0'+data[2:5])[0] >> 4
		# should we check for bottom of stack before the shift ?
		if subtype in PMSI._known:
			return PMSI._known[subtype].unpack(data[5:],label,flags)
		return PMSI.unknown(subtype,data[5:],label,flags)


# ================================================================= PMSINoTunnel
# RFC 6514

class PMSINoTunnel (PMSI):
	TUNNEL_TYPE = 0

	def __init__ (self,label=0,flags=0):
		PMSI.__init__(self,'',label,flags)

	def prettytunnel (self):
		return ''

	@staticmethod
	def unpack (tunnel,label,flags):
		return PMSINoTunnel(label,flags)

PMSINoTunnel.register()


# ======================================================= PMSIIngressReplication
# RFC 6514

class PMSIIngressReplication (PMSI):
	TUNNEL_TYPE = 6

	def __init__ (self,ip,label=0,flags=0,tunnel=None):
		self.ip = ip
		PMSI.__init__(self,tunnel if tunnel else socket.inet_pton(socket.AF_INET,self.ip),label,flags)

	def prettytunnel (self):
		return self.ip

	@staticmethod
	def unpack (tunnel,label,flags):
		ip = socket.inet_ntop(socket.AF_INET,tunnel)
		return PMSIIngressReplication(ip,label,flags,tunnel)

PMSIIngressReplication.register()
