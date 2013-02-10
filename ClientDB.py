#!/usr/bin/python
# -*- coding: utf-8 -*-

try:
	import sqlite3
except ImportError:
	import sqlite as sqlite3

from time import sleep

class DB:
	"""
		Database object. 
		Used for communicating with the SQLite database.
	"""
	
	def __init__(self, db_file):
		"""
			Initializes database. 
			Attempts to creates tables with schemas if needed.
				* db_file - Name of the database file.
			
			For example:
				db = DB('file.db')
		"""
		self.conn = None
		
		self.conn = sqlite3.connect(db_file, encoding='utf-8')
		self.conn.text_factory = lambda x: unicode(x, "utf-8", "ignore")
		
	def get_cursor(self):
		return self.conn.cursor()
	
	def count(self, table, where):
		"""
			Counts the number of tuples in 'table' where the 'where' condition holds
				* table - The table name, a string
				* where - A condition, such as "year == 1999"
			
			Returns # of tuples found in query.
		"""
		cur = self.conn.cursor()
		result = cur.execute('''select count(*) from %s where %s''' % (table, where, )).fetchall()
		#self.conn.commit()
		cur.close()
		return result[0][0]
	
	
	def select(self, what, table, where=''):
		"""
			Executes a SQL SELECT command. Returns tuples
			Type the entire SELECT statement.
			For example:
				
				db = DB('file.db', {'table_name': 'id int primary key'} )
				tuples = db.select('''SELECT * FROM table WHERE id > 0''')
				for result in tuples:
					print result[0] # prints first attribute
					print result[1] # prints second attribute
					...
		"""
		cur = self.conn.cursor()
		query_string = '''SELECT %s FROM %s''' % (what, table)
		if where != '':
			query_string += ''' WHERE %s''' % (where)
		# Great for debugging; print every sql query
		#print query_string
		
		try_again = True
		while try_again:
			try:
				cur.execute(query_string)
				try_again = False
			except Exception:
				sleep(0.1)
		
		results = []
		for result in cur:
			results.append(result)
		cur.close()
		return results
	
	
	def insert(self, table, values):
		"""
			Inserts tuple of values into database.
				* table - The table name, a string
				* values - The tuple to insert into the database.
			Returns row id of tuple inserted, or -1 if error occurred.
		"""
		cur = self.conn.cursor()
		try:
			questions = ''
			for i in xrange(0, len(values)):
				if questions != '': questions += ','
				questions += '%s'
			exec_string = '''insert into %s values (%s)''' % (table, questions)
			result = cur.execute(exec_string, values)
			last_row_id = cur.lastrowid
			cur.close()
			return last_row_id
		except sqlite3.IntegrityError:
			cur.close()
			return -1
	
	
	def commit(self):
		"""
			Commits any changes to the database.
			CHANGES WILL NOT HAPPEN UNLEsS THIS COMMAND IS EXECUTED AFTERWARD!
		"""
		try_again = True
		while try_again:
			try:
				self.conn.commit()
				try_again = False
			except Exception:
				sleep(0.1)
				
	
	def execute(self, statement, values=None):
		"""
			Executes a statement. Similar to the 'select' method, but does not return anything.
		"""
		cur = self.conn.cursor()
		try_again = True
		while try_again:
			try:
				if values == None:
					result = cur.execute(statement)
				else:
					result = cur.execute(statement, values)
				try_again = False
			except:
				sleep(0.1)
		return result
	
