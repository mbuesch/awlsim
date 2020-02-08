def _calc_daycount(y, m, d):
	daysBeforeMonthTab = []
	b = 0
	for _d in (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31):
		daysBeforeMonthTab.append(b)
		b += _d
	daysBeforeYear = (y - 1) * 365 + (y - 1) // 4 - (y - 1) // 100 + (y - 1) // 400
	leap = y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)
	daysBeforeMonth = daysBeforeMonthTab[m - 1] + (1 if (m > 2 and leap) else 0)
	return daysBeforeYear + daysBeforeMonth + d

def _calc_weekday(y, m, d):
	return (_calc_daycount(y, m, d) + 6) % 7

class date(object):
	def __init__(self, year, month, day):
		self.year = year
		self.month = month
		self.day = day

	def __add__(self, other):
		#TODO
		return timedelta()

	def __sub__(self, other):
		if isinstance(other, date):
			return timedelta(_calc_daycount(self.year, self.month, self.day) -
					 _calc_daycount(other.year, other.month, other.day))
		#TODO
		return timedelta()

	def weekday(self):
		return _calc_weekday(self.year, self.month, self.day)

class datetime(object):
	def __init__(self, year=0, month=0, day=0,
		     hour=0, minute=0, second=0, microsecond=0, tzinfo=None):
		self.year = year
		self.month = month
		self.day = day
		self.hour = hour
		self.minute = minute
		self.second = second
		self.microsecond = microsecond
		self.tzinfo = tzinfo

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
		return _calc_weekday(self.year, self.month, self.day)

class timedelta(object):
	def __init__(self, days=0, seconds=0, microseconds=0):
		self.days = days
		self.seconds = seconds
		self.microseconds = microseconds
