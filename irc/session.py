from util import debug, critical, ServerError, CommandError, NickError
from util import replycodes, errorcodes
from transaction import Transaction
import re

class Session(object):
	def __init__(self, conn, User, server, auto_init=True):
		self.conn = conn
		self.User = User
		self.server = server
		self.nick = "*"
		self.current_password = None
		self.transaction = None

		if auto_init:
			self.init()

	def sendall(self, *args, **kwargs):
		return self.conn.sendall(*args, **kwargs)
	def recvall(self, *args, **kwargs):
		return self.conn.recvall(*args, **kwargs)

	def reply(self, code, data):
		nick = self.nick if self.transaction is None else self.transaction.user.nick
		self.sendall(":localhost %s %s %s" % (code, nick, data))
	def error(self, code, data):
		self.reply(errorcodes[code][0], "%s %s" % (errorcodes[code][1], data))
	def ok(self, code, data):
		self.reply(replycodes[code], data)

	def init(self):
		debug("New session")

		while True:
			message = self.recvall()
			if message.strip() == "":
				continue

			if message.startswith("QUIT ") or message == "QUIT":
				if self.transaction is not None:
					self.transaction.finish()
				break

			message = self.parseMessage(message)

			command = message["command"][0].upper() + message["command"][1:].lower()
			command = "command" + command

			transaction = self.transaction or self
			if command in dir(transaction):
				getattr(transaction, command)(*message["params"])
			elif command in ["commandPing", "commandCap"]:
				getattr(self, command)(*message["params"])
			else:
				transaction.error("ERR_UNKNOWNCOMMAND", message["command"])

	def commandCap(self, cmd, *args):
		if cmd == "LS":
			self.commandCapLs(*args)
		elif cmd == "REQ":
			self.commandCapReq(*args)
		elif cmd == "LIST":
			self.commandCapList(*args)
		elif cmd == "END":
			pass

	def commandCapLs(self, version="301"):
		if version == "302":
			self.reply("CAP", "LS :sasl=PLAIN")
		else:
			self.reply("CAP", "LS :sasl")

	def commandCapReq(self, cap):
		if cap != "sasl":
			return

		self.reply("CAP", "ACK :sasl")

	def commandCapList(self):
		self.reply("CAP", "LS :sasl")

	def parseMessage(self, message):
		prefix = None
		if message[0] == ":":
			prefix = message[1:message.index(":")]
			message = message[message.index(":")+1:]

		message = re.split(r" +", message, maxsplit=1)

		command = message[0]

		if len(message) == 1:
			return dict(command=command, params=[])

		params = message[1].strip()

		trailing = None
		try:
			index = params.index(":")
			trailing = params[index+1:]
			params = params[:index].strip()
		except ValueError:
			pass

		params = re.split(r" +", params) if params != "" else []
		if trailing is not None:
			params.append(trailing)

		return dict(command=command, params=params)

	def commandNick(self, nick):
		try:
			self.User.check_nick(nick)
			self.nick = nick
		except NickError as e:
			self.error("ERR_ERRONEUSNICKNAME", str(e))

	def commandUser(self, username, hostname, servername, realname):
		self.username = username
		self.hostname = hostname
		self.servername = servername
		self.realname = realname

		self.transaction = Transaction(
			self.nick, self.username, self.hostname,
			conn=self.conn, session=self, server=self.server
		)

		if self.current_password is not None:
			if not self.transaction.user.auth(self.current_password):
				self.error("ERR_ALREADYREGISTRED", "Invalid password")

	def commandPass(self, password):
		self.current_password = password

	def commandPing(self, server):
		self.sendall(":localhost PONG localhost :%s" % server)