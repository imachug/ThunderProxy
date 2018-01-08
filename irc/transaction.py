from util import debug, critical, ServerError, CommandError
from util import replycodes, errorcodes
import re

class Transaction(object):
	def __init__(self, nick, username, hostname, Channel, conn):
		self.nick = nick
		self.username = username
		self.hostname = hostname
		self.channels = []
		self.Channel = Channel
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

		topic = None
		for channel in channels:
			chan = self.Channel(channel[0], key=channel[1])
			topic = chan.get_topic()
			self.channels.append(chan)

		if topic is None:
			self.ok("RPL_NOTOPIC", "")
		else:
			self.ok("RPL_TOPIC", ":%s" % topic)