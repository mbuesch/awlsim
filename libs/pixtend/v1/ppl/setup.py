from setuptools import setup

setup(name='pixtendlib',
      version='0.1.1',
      description='A Python library to control the PiXtend board.',
      url='https://www.pixtend.de',
      author='Qube Solutions UG',
      author_email='info@pixtend.de',
      license='GPLv3 Open Source License',
      packages=['pixtendlib'],
      zip_safe=False, install_requires=['spidev', 'RPi.GPIO'])
