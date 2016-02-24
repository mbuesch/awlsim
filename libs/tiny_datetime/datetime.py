class date(object):
	def __init__(self, year, month, day):
		#TODO
		pass

	def __add__(self, other):
		#TODO
		return timedelta()

	def __sub__(self, other):
		#TODO
		return timedelta()

	def weekday(self):
		#TODO
		return 1

class datetime(object):
	year = 0
	month = 0
	day = 0
	hour = 0
	minute = 0
	second = 0
	microsecond = 0

	def __init__(self, year=0, month=0, day=0,
		     hour=0, minute=0, second=0, microsecond=0, tzinfo=None):
		#TODO
		pass

	def __add__(self, other):
		#TODO
		return timedelta()

	def __sub__(self, other):
		#TODO
		return timedelta()

	@classmethod
	def now(cls, tz=None):
		#TODO
		return cls.utcnow()

	@classmethod
	def utcnow(cls):
		#TODO
		return cls()

	@classmethod
	def strptime(cls, date_string, format):
		#TODO
		pass

	def weekday(self):
		#TODO
		return 1

class timedelta(object):
	days = 0
	seconds = 0
	microseconds = 0
