#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Author: <Zurdi>


import sys
from io import IOBase
from lib.lib_wb_nbz import LibWb
from lib.lib_log_nbz import Logging
lib_wb_nbz = LibWb()
logger = Logging()


class NBZCore:
	"""Core of the NBZ. This is the module where all the nbz-scripts instructions are executed.

	In the executeInstructions() method, are explained all the logical processes to parse
	and execute properly the list structure generated by the NBZParser module.

	Attributes:
		attributes: dictionary of multiple parameters, paths and structures needed to run the nbz-script
		statements: dictionary of multiple nbz-script statements to execute each when needed

	Methods:
		get_attributes
		execute_instructions
		_assign
		_def
		_func
		_if
		_for
		_while
		get_values
	"""

	def __init__(self, attributes):
		"""Init NBZCore class with his attributes"""

		self.attributes = attributes
		self.statements = {
			'assign': self._assign,
			'def': self._def,
			'func': self._func,
			'if': self._if,
			'for': self._for,
			'while': self._while
		}

	def get_attributes(self):
		"""Returns class attributes attribute

		Returns:
			The class attributes dict"""

		return self.attributes

	def execute_instructions(self, instruction_set=None):
		"""Execute each instruction from instruction_set (recursively on flow control sentences)

		The following structure is how parser converts nbz-script to be executed by this method:
			instruction[0] -> type:
				- assign:       instruction[1] -> id
								instruction[2] -> value | expression
				- def
								instruction[1] -> id
								instruction[2] -> block of sentences

				- func:         instruction[1] -> id
								instruction[2] -> parameters list

				- if:           instruction[1] -> condition
								instruction[2] -> block of sentences (if)
								instruction[3] -> block of sentences (elif or else)
								(instruction[4]) -> block of sentences (else)

				- for(normal):  instruction[1] -> start index
								instruction[2] -> end index
								instruction[3] -> mode (+ | ++ | - | --)
								instruction[4] -> block of sentences

				- for(foreach): instruction[1] -> temporal variable
								instruction[2] -> iterable structure
								instruction[3] -> block of sentences

				- while:        instruction[1] -> condition
								instruction[2] -> block of sentences

		Args:
			instruction_set: list of instructions to be executed
		"""

		# We need to check if this method is called from main script
		# or if it is called from a loop inside the script (like a for loop or a while loop)
		if instruction_set is None:
			instructions = self.attributes['instruction_set']
		else:
			instructions = instruction_set
		for instruction in instructions:
			self.statements[instruction[0]](instruction)

	def _assign(self, instruction):
		var_name = instruction[1]
		var_value = instruction[2]
		self.attributes['variables'][var_name] = self.get_value(var_value)

	def _def(self, instruction):
		func_name = instruction[1]
		func_instructions = instruction[2]
		self.attributes['USER_FUNC'][func_name] = func_instructions

	def _func(self, instruction):
		func_name = instruction[1]
		func_parameters = instruction[2]
		params = []
		for param in func_parameters:
			params.append(self.get_value(param))
		if func_name == 'exit':
			sys.exit(params[0])
		elif func_name == 'browser':
			if self.attributes['browser'] is not None:
				try:
					self.attributes['server'], self.attributes['proxy'], self.attributes['browser'] \
						= lib_wb_nbz.instance_browser(self.attributes['proxy_enabled'], self.attributes['proxy_path'], params)
				except Exception as e:
					logger.log('ERROR', 'Error with browser: {exception}'.format(exception=e))
					sys.exit()
			else:
				logger.log('ERROR', 'Browser already instanced')
		elif func_name == 'export_net_report':
			if self.attributes['proxy_enabled']:
				self.attributes['complete_csv']\
					= self.attributes['NATIVES']['export_net_report'](params, self.attributes['script_name'])
				self.attributes['set_net_report'] = True
			else:
				logger.log('ERROR', 'Can\'t get net report. Proxy not enabled.')
		elif func_name == 'reset_har':
			if self.attributes['proxy_enabled']:
				self.attributes['NATIVES']['reset_har'](self.attributes['set_net_report'],
														self.attributes['complete_csv'],
														self.attributes['browser'].current_url,
														self.attributes['proxy'])
			else:
				logger.log('ERROR', 'Can\'t reset HAR. Proxy not enabled.')
		elif func_name == 'check_net':
			pass
		elif func_name == 'get_parameter':
			pass
		else:
			try:
				try:
					self.attributes['NATIVES'][func_name](self.attributes['browser'], params)
				except Exception as e:
					logger.log('ERROR', 'Error with function {function}: {exception}'.format(function=func_name,
																							 exception=e))
					raise Exception(str(e))
			except LookupError:
				try:
					self.execute_instructions(self.attributes['USER_FUNC'][func_name])
				except LookupError:
					logger.log('ERROR', '{func_name} function not defined.'.format(func_name=func_name))
					raise Exception(str(e))

	def _if(self, instruction):
		if_condition = self.get_value(instruction[1])
		if_instructions = instruction[2]
		try:
			elif_else_statements = instruction[3]
			else_instructions = instruction[4][0][1]
		except LookupError:
			pass
		if if_condition:
			self.execute_instructions(if_instructions)
		else:
			if len(instruction) == 4:  # If statement have elif OR else
				if elif_else_statements[0][0] == 'elif':
					for elif_ in elif_else_statements:
						elif_condition = self.get_value(elif_[1])
						elif_instructions = elif_[2]
						if elif_condition:
							self.execute_instructions(elif_instructions)
							break
				elif elif_else_statements[0][0] == 'else':
					else_instructions = elif_else_statements[0][1]
					self.execute_instructions(else_instructions)
			elif len(instruction) == 5:  # If statement have elif AND else
				elif_done = False
				for elif_ in elif_else_statements:
					elif_condition = self.get_value(elif_[1])
					elif_instructions = elif_[2]
					if elif_condition:
						elif_done = True
						self.execute_instructions(elif_instructions)
						break
				if not elif_done:
					self.execute_instructions(else_instructions)

	def _for(self, instruction):
		if len(instruction) == 4:  # Foreach
			element = self.get_value(instruction[1])
			structure = self.attributes['variables'][self.get_value(instruction[2])]
			foreach_instructions = instruction[3]
			for iterator_element in structure:
				try:
					if isinstance(structure, file):
						self.attributes['variables'][element] = iterator_element[0:-1]  # Avoiding newline character
					else:
						self.attributes['variables'][element] = iterator_element  # All other structure types
				except NameError:
					if isinstance(structure, IOBase):
						self.attributes['variables'][element] = iterator_element[0:-1]  # Avoiding newline character
					else:
						self.attributes['variables'][element] = iterator_element  # All other structure types
				self.execute_instructions(foreach_instructions)
		else:  # Standard For
			init_index = self.get_value(instruction[1])
			fin_index = self.get_value(instruction[2])
			op_counters = {'+': 1, '++': 2, '-': -1, '--': -2}
			counter = op_counters[instruction[3]]
			for_instructions = instruction[4]
			for i in range(init_index, fin_index, counter):
				self.execute_instructions(for_instructions)

	def _while(self, instruction):
		while_condition = instruction[1]
		while_instructions = instruction[2]
		while self.get_value(while_condition):
			self.execute_instructions(while_instructions)

	def get_value(self, sub_instruction):
		"""Local function inside executeInstructions() method, that is just used for it.

		Get the value from some distinct structures:
			- direct value or variable value of a parameter
			- resolve arithmetic expressions
			- resolve boolean expressions
			- resolve function return value

		Args:
			sub_instruction: expression that can be one of the previous described structures.
		Returns:
			The value of the expression
		"""

		try:
			if isinstance(sub_instruction, list):
				if len(sub_instruction) > 0:
					if sub_instruction[0] == 'var':
						return self.attributes['variables'][sub_instruction[1]]
					elif sub_instruction[0] == 'value':
						return sub_instruction[1]
					elif sub_instruction[0] == 'arithm':
						if sub_instruction[3] == '+':
							op_1 = self.get_value(sub_instruction[1])
							op_2 = self.get_value(sub_instruction[2])
							if isinstance(op_1, str) or isinstance(op_2, str):
								if isinstance(op_1, unicode):
									op_1 = op_1.encode('utf-8')
								if isinstance(op_1, unicode):
									op_2 = op_2.encode('utf-8')
								return '{op_1}{op_2}'.format(op_1=str(op_1),
															 op_2=str(op_2))
							else:
								return op_1 + op_2
						else:
							return eval('{op_1}{operand}{op_2}'.format(op_1=self.get_value(sub_instruction[1]),
																	   operand=sub_instruction[3],
																	   op_2=self.get_value(sub_instruction[2])))
					elif sub_instruction[0] == 'boolean':
						if sub_instruction[3] != 'not':
							op_1 = self.get_value(sub_instruction[1])
							op_2 = self.get_value(sub_instruction[2])
							if isinstance(op_1, str) or isinstance(op_1, unicode):
								op_1 = "'{op_1}'".format(op_1=op_1)
							if isinstance(op_2, str) or isinstance(op_2, unicode):
								op_2 = "'{op_2}'".format(op_2=op_2)
							return eval('{op_1} {operand} {op_2}'.format(op_1=self.get_value(op_1),
																		operand=sub_instruction[3],
																		op_2=self.get_value(op_2)))
						else:
							return not self.get_value(sub_instruction[1])
					elif sub_instruction[0] == 'func':
						sub_params = []
						for sub_param in sub_instruction[2]:
							sub_params.append(self.get_value(sub_param))
						try:
							if sub_instruction[1] == 'check_net':
								return self.attributes['NATIVES']['check_net'](self.attributes['proxy'].har,
																			sub_params)
							elif sub_instruction[1] == 'get_parameter':
								return self.attributes['NATIVES']['get_parameter'](self.attributes['script_parameters'], sub_params)
							else:
								return self.attributes['NATIVES'][sub_instruction[1]](self.attributes['browser'],
																					sub_params)
						except Exception as e:
							raise Exception(str(e))
					else:
						return sub_instruction
				else:
					return sub_instruction
			else:
				return sub_instruction
		except Exception as e:
			raise Exception(str(e))
