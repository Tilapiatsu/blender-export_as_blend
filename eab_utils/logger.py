
class Logger(object):
	def __init__(self, addon_name='ROOT', print=False):
		self.addon_name = addon_name
		self.print = print

	def info(self, message):
		self.print_message(message, 'INFO')

	def debug(self, message):
		self.print_message(message, 'DEBUG')

	def warning(self, message):
		self.print_message(message, 'WARNING')

	def error(self, message):
		self.print_message(message, 'ERROR')

	def print_message(self, message, mode):
		if self.print:
			print(f'{self.addon_name} : {mode} : {message}')
