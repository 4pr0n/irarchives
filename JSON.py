#!/usr/bin/python

class json(object):
	"""
		Simplified JSON parser. Only implements loads()
	"""
	# Whitespaces that we ignore when parsing between JSON values
	WHITESPACE = [' ', '\t' ,'\n', '\r', '\f']
	
	@staticmethod
	def pretty_string(toprint, indent=0):
		""" 
			Returns string containing all keys and values in a dict. 
			Makes it 'Pretty'.
		"""
		SEP = '  ' # Separator. May want to use tab \t
		if isinstance(toprint, dict):
			result = []
			for key, value in toprint.iteritems():
				result.append(SEP * indent + '%s: {' % (key))
				result.append(json.pretty_string(value, indent + 1))
				result.append(SEP * indent + '},')
			#result[-1] = result[-1][:-1]
			return '\n'.join(result)
		
		elif isinstance(toprint, list):
			templist = []
			for top in toprint:
				templist.append(json.pretty_string(top, indent + 1) + ",")
			#templist[-1] = templist[-1][:-1]
			return '\n'.join(templist)
		elif isinstance(toprint, basestring):
			return '%s"%s"' % (SEP * indent, toprint)
		elif isinstance(toprint, bool):
			return '%s%s' % (SEP * indent, str(toprint))
		elif isinstance(toprint, int):
			return '%s%d' % (SEP * indent, toprint)
		elif isinstance(toprint, float):
			return '%s%f' % (SEP * indent, toprint)
			
		elif toprint == None:
			return '%sNone' % (SEP * indent)
		
		return 'unknown type: %s' % str(type(toprint))
		
	@staticmethod
	def fix_tuple(start_index, value, end_index):
		"""
			the loads() method usually returns a tuple giving information
			on the next place in the text to parse.
			If the user calls loads with no arguments (or index = 0), then
			the user expects a single value back ... not a tuple.
			This method chooses what to return to the user:
				 * The value, if the starting index is 0
				 * A tuple containing the value and the current index
		"""
		if start_index == 0: return value
		else:                return (value, end_index)
	
	@staticmethod
	def loads(text, start_index=0):
		"""
			Gets next JSON value in 'text', starting at 'index'.
			Returns tuple:
				* value (string, dict, list)
				* Index in 'text' where value ends
			Returns  (None, len(text)) if unable to parse text
			...such as unclosed string literals, or incomplete dicts
		"""
		# Debug information
		#print '\t%s\t%d' % (text.replace('\n', ' ').replace('\t', ' '), index)
		#print '\t%s' % (''.join(str(x % 10) for x in xrange(0, 100)))
		
		index = start_index
		while index < len(text) and text[index] in json.WHITESPACE: index += 1
		c = text[index]
		
		# String
		if c == '"':
			start = index + 1
			tempi = start
			while True:
				end = text.find('"', tempi)
				if end == -1: return json.fix_tuple(start_index, None, len(text))
				if text[end-1] == '\\':
					if text[end-2] != '\\': 
						tempi = end + 1
						continue
				break
			result = json.convert_json_string(text[start:end])
			return json.fix_tuple(start_index, result, end + 1)
		
		# Dictionary
		elif c == '{':
			index += 1
			result = {}
			while index < len(text) and text[index] != '}':
				while index < len(text) and text[index] in json.WHITESPACE: index += 1
				if index >= len(text): return json.fix_tuple(start_index, None, len(text))
				(key, index) = json.loads(text, index)
				
				while index < len(text) and text[index] in json.WHITESPACE: index += 1
				# We expect a colon to separate the key and value
				if index >= len(text) or text[index] != ':': return json.fix_tuple(start_index, None, len(text))
				(value, index) = json.loads(text, index + 1)
				result[key] = value
				while index < len(text) and text[index] in json.WHITESPACE: index += 1
				if index >= len(text) or text[index] != ',': break
				index += 1
			
			return json.fix_tuple(start_index, result, index + 1)
		
		# List
		elif c == '[':
			index += 1
			result = []
			while index < len(text) and text[index] != ']':
				while index < len(text) and text[index] in json.WHITESPACE: index += 1
				if index >= len(text) or text[index] == ']': break
				if text[index] == ',': 
					index += 1
					continue
				elif text[index] == ':': return json.fix_tuple(start_index, None, len(text))
				(value, index) = json.loads(text, index)
				result.append(value)
			return json.fix_tuple(start_index, result, index + 1)
		
		# Null type
		elif text[index:index+len('null')].lower() == 'null':
			return json.fix_tuple(start_index, None, index + len('null'))
		
		# Boolean
		elif text[index:index+len('true')].lower() == 'true':
			return json.fix_tuple(start_index, True, index + len('true'))
		elif text[index:index+len('false')].lower() == 'false':
			return json.fix_tuple(start_index, False, index + len('false'))
		
		# Integer/float
		elif c == '-' or c.isdigit():
			result = ''
			while c.isdigit() or c == '.':
				result += c
				index  += 1
				c = text[index]
			try:
				if '.' in result: return json.fix_tuple(start_index, float(result), index)
				else:             return json.fix_tuple(start_index, int(result), index)
			except ValueError:
				return None
		
		else:
			print 'not ready to handle "%s"' % (c)
			tempmin = index - 10
			if tempmin < 0: tempmin = 0
			print '\t', text[tempmin:index+10]
			print int('asfklasjf')
			# Can only handle strings, lists, and dicts right now
			return json.fix_tuple(start_index, None, len(text))
	
	@staticmethod
	def convert_json_string(text):
		""" 
			Converts JSON-formatted string to a python string.
			Returns None if improperly formatted (e.g. invalid escape char)
		"""
		result = ''
		index = 0
		while index < len(text):
			c = text[index]
			if c == '\\' and index + 1 < len(text):
				index += 1
				c = text[index]
				if   c == 'n': c = '\n'
				elif c == 'f': c = '\f'
				elif c == 'b': c = '\b'
				elif c == 'r': c = '\r'
				elif c == 't': c = '\t'
				
				elif c == 'u' and index + 4 < len(text):
					# Unicode
					next4 = text[index+1:index+5]
					uni = int(next4, 16)
					c = unichr(uni)
					index += 4
				
				# Redundancy
				elif c == '"': c  = '"'
				elif c == '/': c  = '/'
				elif c == '\\': c = '\\'
				else:
					# Unexpected escaped character
					index += 1
					continue
			result += c
			index += 1
		return result
	
	@staticmethod
	def string_to_json(text):
		""" 
			Convert string to JSON-formatted text.
		"""
		result = ''
		for char in text:
			c = char
			if c == '\n': c = '\\n'
			elif c == '\f': c = '\\f'
			elif c == '\b': c = '\\b'
			elif c == '\r': c = '\\r'
			elif c == '\t': c = '\\t'
			elif c == '\\': c = '\\\\'
			elif c == '"':  c = '\\"'
			elif c == '/':  c = '\\/'
			elif ord(c) > 128:
				# Replace unicode chars w/ 
				if len(result) == 0 or result[-1] != '?':
					c = '?'
				else: c = ''
			result += c
		return result
	
	
	@staticmethod
	def dumps(dict_to_json):
		""" 
			Converts given dict into JSON-formatted string
		"""
		if isinstance(dict_to_json, basestring):
			return '"%s"' % json.string_to_json(dict_to_json)
		elif isinstance(dict_to_json, bool):
			return '%s' % (str(dict_to_json))
		elif isinstance(dict_to_json, int):
			return '%d' % (dict_to_json)
		elif isinstance(dict_to_json, float):
			return '%f' % (dict_to_json)
			
		elif isinstance(dict_to_json, list):
			templist = []
			for top in dict_to_json:
				templist.append(json.dumps(top))
			return '[' + ', '.join(templist) + ']'
		elif isinstance(dict_to_json, dict):
			result = []
			for key, value in dict_to_json.iteritems():
				result.append('"%s": ' % (key))
				result.append(json.dumps(value))
				result.append(', ')
			if len(result) > 0:
				result[-1] = result[-1][:-2]
			return '{' + ''.join(result) + '}'
		
		elif dict_to_json == None:
			return 'null'

if __name__ == '__main__':
	f = open('json_reddit.json', 'r')
	txt = f.read()
	f.close()
	
	result = json.loads(txt)[0]
	pretty = json.pretty_string(result)
	
	'''
	result_real = json_real.loads(txt)
	pretty_real = json.pretty_string(result_real)
	
	pretty      = pretty #[500:600]
	pretty_real = pretty_real #[500:600]

	print 'mine:'
	print pretty
	print '-------------------\ntheirs:'
	print pretty_real
	print '-------------------'
	
	print '\n\n'
	if not pretty == pretty_real:
		print len(pretty)
		print len(pretty_real)
	'''
