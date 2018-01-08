from util import debug, critical, ServerError, CommandError
from util import replycodes, errorcodes
import re

class Transaction(object):
	def __init__(self, nick, username, hostname, Channel, User, conn):
		self.nick = nick
		self.username = username
		self.hostname = hostname
		self.channels = []
		self.Channel = Channel
		self.user = User(nick)
		self.conn = conn
		self.init()

	def sendall(self, *args, **kwargs):
		return self.conn.sendall(*args, **kwargs)
	def recvall(self, *args, **kwargs):
		return self.conn.recvall(*args, **kwargs)

	def reply(self, code, data):
		self.sendall(":localhost %s %s %s" % (code, self.nick, data))
	def error(self, code, data):
		self.reply(errorcodes[code][0], "%s %s" % (errorcodes[code][1], data))
	def ok(self, code, data):
		self.reply(replycodes[code], data)

	def init(self):
		self.ok(
			"RPL_WELCOME",
			":Welcome to the Internet Relay Network %s!%s@%s" % (self.nick, self.username, self.hostname)
		)

	def commandJoin(self, channels, keys=None):
		channels = channels.split(",")
		keys = keys.split(",") if keys is not None else []

		channels = map(None, channels, keys) # This is like zip() but with padding

		for channel in channels:
			chan = self.get_channel(channel[0])
			if chan.get_key() != channel[1]:
				self.error("ERR_BADCHANNELKEY", "")
				return

			chan.connect(self.nick)

			# Specify online users
			online = chan.get_online()
			online = [(nick, chan.get_user(nick)) for nick in online]
			online = [
				"@" + user[0] if user[1].is_admin() else
				"+" + user[0] if user[1].is_moderator() else
				user[0]

				for user in online
			]
			online = " ".join(online)

			self.ok("RPL_NAMREPLY", "@ %s :%s" % (channel[0], online))
			self.ok("RPL_ENDOFNAMES", "%s :End of /NAMES list." % channel[0])

	def get_channel(self, channel):
		chan = self.Channel(channel)
		self.channels.append(chan)
		return chan

	def commandAway(self, reason=None):
		if reason is None:
			self.user.set_away(False)
			self.ok("RPL_UNAWAY", "")
		else:
			self.user.set_away(True, reason=reason)
			self.ok("RPL_NOWAWAY", "")