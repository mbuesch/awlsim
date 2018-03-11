from setuptools import setup

setup(name='pixtendlibv2',
      version='0.1.1',
      description='Python module for PiXtend V2 boards.',
      url='http://www.pixtend.de',
      author='Qube Solutions UG',
      author_email='info@pixtend.de',
      license='GPLv3 Open Source License',
      packages=['pixtendv2core', 'pixtendv2s'],
      zip_safe=False, install_requires=['spidev', 'RPi.GPIO'])
